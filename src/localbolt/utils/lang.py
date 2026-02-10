"""
Language detection utility — determines source language from file extension.
This module is the single source of truth for language routing throughout LocalBolt.
"""
from pathlib import Path
from enum import Enum


class Language(str, Enum):
    CPP = "cpp"
    RUST = "rust"
    UNKNOWN = "unknown"


# Extensions that map to each language
_EXT_MAP = {
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".c": Language.CPP,
    ".C": Language.CPP,
    ".rs": Language.RUST,
}

SUPPORTED_EXTENSIONS = set(_EXT_MAP.keys())


def detect_language(file_path: str) -> Language:
    """Detect language from file extension."""
    ext = Path(file_path).suffix
    return _EXT_MAP.get(ext, Language.UNKNOWN)


def is_supported(file_path: str) -> bool:
    """Return True if the file extension is supported."""
    return Path(file_path).suffix in SUPPORTED_EXTENSIONS


def source_label(lang: Language) -> str:
    """Return a human-readable label for the language (used in UI)."""
    if lang == Language.RUST:
        return "RUST SOURCE"
    return "C++ SOURCE"
