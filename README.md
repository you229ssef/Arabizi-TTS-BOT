# Arabizi Tunisian Discord TTS bot

This is a free/local Discord text-to-speech bot for Tunisian Arabizi. Use `/speak`
while you are in a voice channel: the bot joins that same channel and reads only
new messages from the text channel where `/speak` was used. `/pause` toggles
pause/resume and `/leave` stops the session and disconnects.

## What it supports

- Python 3, `discord.py`, and Discord slash commands.
- FIFO speech queue with a configurable queue limit.
- Common Arabizi mappings such as `3` -> `ع`, `7` -> `ح`, `5` -> `خ`,
  `9` -> `ق`, plus common `ch`, `sh`, `kh`, and `gh` spellings.
- Bot-message filtering, per-user cooldowns, message-length limits, cleanup,
  and Discord voice reconnect support.
- No secrets in the repository; configure the token through environment variables.

Free offline TTS engines generally do **not** provide a real Tunisian-accent
voice. This project normalizes Arabizi into Arabic script so an installed Arabic
or multilingual system voice has a better chance of pronouncing it, but the
result depends on the voice available on the host. It is not a guaranteed
Tunisian accent.

## Local setup

1. Create a Discord application and bot, then enable **Message Content Intent**
   under the bot settings.
2. Invite it with the `bot` and `applications.commands` scopes and the
   permissions to view/send messages, connect, and speak.
3. Install system dependencies:

   ```bash
   # Debian/Ubuntu
   sudo apt-get update
   sudo apt-get install -y ffmpeg espeak-ng libespeak1
   ```

4. Create an environment and install Python dependencies:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

5. Set `DISCORD_TOKEN` in `.env`, then run:

   ```bash
   python bot.py
   ```

## SillyDev free-tier deployment

Create a Python 3 service using this repository. Use `pip install -r
requirements.txt` as the install command and `python bot.py` as the start
command. Add `DISCORD_TOKEN` as a secret/environment variable, not as a file
committed to Git. If SillyDev permits an apt/system package section, add
`ffmpeg` and `espeak-ng`; if it does not, the bot can connect but cannot
produce speech because Discord playback needs FFmpeg and local synthesis needs
a speech backend. Check the service logs for the explicit missing-dependency
error.

Environment variables:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `DISCORD_TOKEN` | required | Discord bot token |
| `MAX_MESSAGE_LENGTH` | `300` | Ignore longer messages |
| `MESSAGE_COOLDOWN_SECONDS` | `1.5` | Per-user speech cooldown |
| `MAX_QUEUE_SIZE` | `25` | Maximum pending messages per server |
| `TTS_RATE` | `155` | Local voice speed |
| `TTS_VOLUME` | `1.0` | Local voice volume |

The bot intentionally does not read message history; it only speaks new
messages after `/speak` starts. It keeps one session per server and replaces an
existing session when `/speak` is run again.

## Tests

The dependency-light tests cover Arabizi normalization and FIFO queue limits:

```bash
python -m unittest discover -s tests -v
```
