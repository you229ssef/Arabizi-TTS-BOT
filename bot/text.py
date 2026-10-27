"""Arabizi/Tunisian text normalization for local speech engines."""

from __future__ import annotations

import re


_DIGIT_MAP = {
    "2": "ء",
    "3": "ع",
    "4": "غ",
    "5": "خ",
    "6": "ط",
    "7": "ح",
    "8": "ظ",
    "9": "ق",
}

_LATIN_MAP = {
    "ch": "ش",
    "sh": "ش",
    "kh": "خ",
    "gh": "غ",
    "th": "ث",
    "dh": "ذ",
    "aa": "ا",
    "ee": "ي",
    "oo": "و",
}

_LATIN_CHAR_MAP = {
    "a": "ا",
    "b": "ب",
    "c": "ك",
    "d": "د",
    "e": "",
    "f": "ف",
    "g": "ج",
    "h": "ه",
    "i": "ي",
    "j": "ج",
    "k": "ك",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "o": "و",
    "p": "ب",
    "q": "ق",
    "r": "ر",
    "s": "س",
    "t": "ت",
    "u": "و",
    "v": "ف",
    "w": "و",
    "x": "خ",
    "y": "ي",
    "z": "ز",
}

_WORD_RE = re.compile(r"[A-Za-z0-9']+|[\u0600-\u06ff]+|[^\w\s]+|\s+", re.UNICODE)


def _normalize_word(word: str) -> str:
    lowered = word.lower()
    lowered = lowered.replace("3'", "غ").replace("7'", "خ")
    for latin, arabic in sorted(_LATIN_MAP.items(), key=lambda item: -len(item[0])):
        lowered = lowered.replace(latin, arabic)

    translated: list[str] = []
    for character in lowered:
        translated.append(_DIGIT_MAP.get(character, _LATIN_CHAR_MAP.get(character, character)))
    return "".join(translated)


def normalize_arabizi(text: str) -> str:
    """Convert common Arabizi characters to Arabic script for better local TTS.

    Existing Arabic text, punctuation, and whitespace are preserved. Unknown Latin
    words remain Latin so names and URLs are not unexpectedly changed.
    """

    if not text or not text.strip():
        return ""

    parts: list[str] = []
    for match in _WORD_RE.finditer(text.strip()):
        value = match.group(0)
        if re.fullmatch(r"[A-Za-z0-9']+", value):
            parts.append(_normalize_word(value))
        else:
            parts.append(value)
    return "".join(parts)
