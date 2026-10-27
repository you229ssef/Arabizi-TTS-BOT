import unittest

from bot.text import normalize_arabizi


class NormalizeArabiziTests(unittest.TestCase):
    def test_common_tunisian_arabizi_digits(self) -> None:
        self.assertEqual(normalize_arabizi("3aslema 7abibi"), "عاسلما حابيبي")

    def test_latin_digraphs_and_punctuation(self) -> None:
        self.assertEqual(normalize_arabizi("chneya?"), "شنيا?")

    def test_empty_text(self) -> None:
        self.assertEqual(normalize_arabizi("   "), "")


if __name__ == "__main__":
    unittest.main()
