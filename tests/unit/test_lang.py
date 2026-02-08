"""Unit tests for language detection utility."""
import pytest
from localbolt.utils.lang import detect_language, Language, is_supported, source_label


class TestLanguageDetection:
    """Test detect_language correctly identifies source file languages."""

    def test_cpp_extensions(self):
        assert detect_language("main.cpp") == Language.CPP
        assert detect_language("main.cc") == Language.CPP
        assert detect_language("main.cxx") == Language.CPP
        assert detect_language("main.c") == Language.CPP

    def test_rust_extension(self):
        assert detect_language("main.rs") == Language.RUST

    def test_unknown_extension(self):
        assert detect_language("main.py") == Language.UNKNOWN
        assert detect_language("main.java") == Language.UNKNOWN
        assert detect_language("Makefile") == Language.UNKNOWN

    def test_full_paths(self):
        assert detect_language("/home/user/project/src/main.rs") == Language.RUST
        assert detect_language("/home/user/project/src/main.cpp") == Language.CPP

    def test_is_supported(self):
        assert is_supported("main.cpp")
        assert is_supported("main.cc")
        assert is_supported("main.rs")
        assert not is_supported("main.py")
        assert not is_supported("main.java")

    def test_source_label(self):
        assert source_label(Language.RUST) == "RUST SOURCE"
        assert source_label(Language.CPP) == "C++ SOURCE"
