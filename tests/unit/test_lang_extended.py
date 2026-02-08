"""
Extended edge case tests for language detection (lang.py).
"""
import pytest
from localbolt.utils.lang import detect_language, Language, is_supported, source_label, SUPPORTED_EXTENSIONS


class TestLanguageEdgeCases:
    """Edge cases for language detection."""

    def test_no_extension(self):
        assert detect_language("Makefile") == Language.UNKNOWN
        assert detect_language("README") == Language.UNKNOWN

    def test_hidden_file(self):
        assert detect_language(".gitignore") == Language.UNKNOWN

    def test_double_extension(self):
        """Only the last extension matters."""
        assert detect_language("main.test.cpp") == Language.CPP
        assert detect_language("main.test.rs") == Language.RUST

    def test_uppercase_C_extension(self):
        """Capital .C is a valid C++ extension."""
        assert detect_language("main.C") == Language.CPP

    def test_empty_string(self):
        assert detect_language("") == Language.UNKNOWN

    def test_just_extension(self):
        """A bare extension like '.cpp' has no suffix per pathlib — it's the stem."""
        # Path(".cpp").suffix == "" because the whole thing is treated as a stem
        assert detect_language(".cpp") == Language.UNKNOWN
        assert detect_language(".rs") == Language.UNKNOWN

    def test_path_with_spaces(self):
        assert detect_language("/home/user/my project/main.cpp") == Language.CPP
        assert detect_language("/home/user/my project/main.rs") == Language.RUST

    def test_windows_path(self):
        assert detect_language("C:\\Users\\user\\main.cpp") == Language.CPP
        assert detect_language("C:\\Users\\user\\main.rs") == Language.RUST


class TestIsSupportedEdgeCases:
    """Edge cases for is_supported."""

    def test_no_extension_not_supported(self):
        assert not is_supported("Makefile")

    def test_empty_not_supported(self):
        assert not is_supported("")

    def test_cxx_supported(self):
        assert is_supported("main.cxx")

    def test_all_supported_extensions_documented(self):
        """All extensions in the map should be in SUPPORTED_EXTENSIONS."""
        for ext in [".cpp", ".cc", ".cxx", ".c", ".C", ".rs"]:
            assert ext in SUPPORTED_EXTENSIONS


class TestSourceLabel:
    """Test source_label for UI display."""

    def test_unknown_defaults_to_cpp(self):
        """UNKNOWN language should fall through to C++ label (default)."""
        result = source_label(Language.UNKNOWN)
        assert result == "C++ SOURCE"

    def test_rust_label(self):
        assert source_label(Language.RUST) == "RUST SOURCE"

    def test_cpp_label(self):
        assert source_label(Language.CPP) == "C++ SOURCE"


class TestLanguageEnum:
    """Test Language enum values and string behavior."""

    def test_enum_values(self):
        assert Language.CPP.value == "cpp"
        assert Language.RUST.value == "rust"
        assert Language.UNKNOWN.value == "unknown"

    def test_str_comparison(self):
        """Language extends str, so it should compare equal to its value."""
        assert Language.CPP == "cpp"
        assert Language.RUST == "rust"
        assert Language.UNKNOWN == "unknown"

    def test_all_members(self):
        members = list(Language)
        assert len(members) == 3
