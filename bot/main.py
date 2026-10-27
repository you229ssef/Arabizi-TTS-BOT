"""Discord bot entrypoint and voice-session lifecycle."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv

from .queue import SpeechItem, SpeechQueue
from .text import normalize_arabizi
from .tts import LocalTTS

LOG = logging.getLogger("arabizi_tts")


@dataclass
class VoiceSession:
    voice: discord.VoiceClient
    text_channel_id: int
    queue: SpeechQueue
    tts: LocalTTS
    worker: asyncio.Task[None] | None = None
    paused: bool = False

    def start_worker(self) -> None:
        self.worker = asyncio.create_task(self._run(), name=f"tts-worker-{self.voice.channel.id}")

    async def _run(self) -> None:
        while not self.queue.closed:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            try:
                while self.paused and not self.queue.closed:
                    await asyncio.sleep(0.25)
                if self.queue.closed:
                    continue
                audio_path = await self.tts.synthesize(item.text)
                try:
                    await self._play(audio_path)
                finally:
                    audio_path.unlink(missing_ok=True)
            except Exception:
                LOG.exception("Could not synthesize or play speech")
            finally:
                self.queue.task_done()

    async def _play(self, audio_path: Path) -> None:
        if not self.voice.is_connected():
            return
        finished = asyncio.Event()
        loop = asyncio.get_running_loop()

        def after(error: Exception | None) -> None:
            if error:
                LOG.error("Discord voice playback failed: %s", error)
            loop.call_soon_threadsafe(finished.set)

        self.voice.play(discord.FFmpegPCMAudio(str(audio_path)), after=after)
        await finished.wait()

    async def stop(self) -> None:
        self.queue.close()
        if self.worker and not self.worker.done():
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
        if self.voice.is_connected():
            await self.voice.disconnect(force=True)


class ArabiziBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.sessions: dict[int, VoiceSession] = {}
        self.cooldowns: dict[tuple[int, int], float] = {}
        self.max_length = int(os.getenv("MAX_MESSAGE_LENGTH", "300"))
        self.cooldown_seconds = float(os.getenv("MESSAGE_COOLDOWN_SECONDS", "1.5"))
        self.max_queue_size = int(os.getenv("MAX_QUEUE_SIZE", "25"))
        self.tts_rate = int(os.getenv("TTS_RATE", "155"))
        self.tts_volume = float(os.getenv("TTS_VOLUME", "1.0"))

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_ready(self) -> None:
        LOG.info("Connected as %s", self.user)

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if not self.user or member.id != self.user.id or after.channel is not None:
            return
        session = self.sessions.pop(member.guild.id, None)
        if session:
            session.queue.close()
            if session.worker and not session.worker.done():
                session.worker.cancel()
                await asyncio.gather(session.worker, return_exceptions=True)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        session = self.sessions.get(message.guild.id if message.guild else 0)
        if not session or message.channel.id != session.text_channel_id:
            return
        if len(message.content) > self.max_length:
            return
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        if now - self.cooldowns.get(key, 0) < self.cooldown_seconds:
            return
        self.cooldowns[key] = now
        normalized = normalize_arabizi(message.content)
        if normalized:
            queued = await session.queue.put(SpeechItem(normalized, message.author.id))
            if not queued:
                LOG.warning("Speech queue full in guild %s", message.guild.id)

    async def start_session(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
            return
        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        old = self.sessions.pop(interaction.guild.id, None)
        if old:
            await old.stop()
        try:
            voice = await voice_state.channel.connect(reconnect=True)
        except (discord.ClientException, discord.Forbidden) as exc:
            await interaction.followup.send(f"Could not join that voice channel: {exc}", ephemeral=True)
            return
        session = VoiceSession(
            voice=voice,
            text_channel_id=interaction.channel_id,
            queue=SpeechQueue(self.max_queue_size),
            tts=LocalTTS(self.tts_rate, self.tts_volume),
        )
        self.sessions[interaction.guild.id] = session
        session.start_worker()
        await interaction.followup.send(
            f"Joined **{voice_state.channel.name}**. I will read messages from {interaction.channel.mention}.",
            ephemeral=True,
        )

    async def stop_session(self, interaction: discord.Interaction, leave: bool = False) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
            return
        session = self.sessions.get(interaction.guild.id)
        if not session:
            await interaction.response.send_message("There is no active speech session.", ephemeral=True)
            return
        if leave:
            self.sessions.pop(interaction.guild.id, None)
            await session.stop()
            await interaction.response.send_message("Left the voice channel.", ephemeral=True)
            return
        session.paused = not session.paused
        await interaction.response.send_message(
            "Speech paused." if session.paused else "Speech resumed.", ephemeral=True
        )


def create_bot() -> ArabiziBot:
    bot = ArabiziBot()

    @bot.tree.command(name="speak", description="Join your voice channel and read this channel's chat")
    async def speak(interaction: discord.Interaction) -> None:
        await bot.start_session(interaction)

    @bot.tree.command(name="pause", description="Pause or resume reading chat")
    async def pause(interaction: discord.Interaction) -> None:
        await bot.stop_session(interaction)

    @bot.tree.command(name="leave", description="Stop reading and leave voice chat")
    async def leave(interaction: discord.Interaction) -> None:
        await bot.stop_session(interaction, leave=True)

    return bot


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN is required; copy .env.example to .env and set it.")
    create_bot().run(token)


if __name__ == "__main__":
    main()
