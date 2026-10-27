import asyncio
import unittest

from bot.queue import SpeechItem, SpeechQueue


class SpeechQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_fifo_order(self) -> None:
        queue = SpeechQueue(maxsize=2)
        self.assertTrue(await queue.put(SpeechItem("first", 1)))
        self.assertTrue(await queue.put(SpeechItem("second", 2)))
        self.assertFalse(await queue.put(SpeechItem("third", 3)))
        first = await queue.get()
        second = await queue.get()
        self.assertEqual([first.text, second.text], ["first", "second"])
        queue.task_done()
        queue.task_done()
        await asyncio.wait_for(queue.join(), timeout=0.1)

    async def test_close_rejects_new_items(self) -> None:
        queue = SpeechQueue()
        queue.close()
        self.assertFalse(await queue.put(SpeechItem("ignored", 1)))


if __name__ == "__main__":
    unittest.main()

