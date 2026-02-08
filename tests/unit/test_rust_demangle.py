"""Unit tests for Rust symbol demangling and simplification."""
import pytest
from unittest.mock import patch, MagicMock
from localbolt.parsing.rust_demangle import (
    demangle_rust,
    simplify_rust_symbols,
    has_rustfilt,
)


class TestHasRustfilt:
    """Test rustfilt detection."""

    def test_found(self):
        with patch("shutil.which", return_value="/usr/bin/rustfilt"):
            assert has_rustfilt() is True

    def test_not_found(self):
        with patch("shutil.which", return_value=None):
            assert has_rustfilt() is False


class TestDemangleRust:
    """Test Rust demangling with and without rustfilt."""

    def test_fallback_when_no_tools(self):
        with patch("shutil.which", return_value=None):
            result = demangle_rust("_ZN4test4main17h1234567890abcdefE")
            assert "_ZN4test4main" in result
            assert "WARN" in result

    def test_demangling_with_rustfilt(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("test::main\n", "")
        mock_proc.returncode = 0

        with patch("shutil.which", return_value="/usr/bin/rustfilt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_rust("_ZN4test4main17h1234567890abcdefE")
                assert "test::main" in result

    def test_graceful_on_rustfilt_error(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "error")
        mock_proc.returncode = 1

        with patch("shutil.which", return_value="/usr/bin/rustfilt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                original = "_ZN4test4main17h1234567890abcdefE"
                result = demangle_rust(original)
                # Should return original text on error
                assert original in result


class TestSimplifyRustSymbols:
    """Test Rust symbol simplification."""

    def test_removes_hash_suffix(self):
        result = simplify_rust_symbols("example::main::h1a2b3c4d5e6f7a8b")
        assert "::h1a2b3c4d5e6f7a8b" not in result
        assert "example::main" in result

    def test_shortens_alloc_vec(self):
        result = simplify_rust_symbols("alloc::vec::Vec<i32>")
        assert result == "Vec<i32>"

    def test_shortens_alloc_string(self):
        result = simplify_rust_symbols("alloc::string::String")
        assert result == "String"

    def test_shortens_core_fmt(self):
        result = simplify_rust_symbols("core::fmt::Display")
        assert result == "fmt::Display"

    def test_passthrough_plain_instructions(self):
        result = simplify_rust_symbols("push rbp")
        assert result == "push rbp"

    def test_passthrough_cpp_symbols(self):
        """Ensure C++ symbols are NOT affected by Rust simplification."""
        result = simplify_rust_symbols("std::vector<int>::push_back")
        assert result == "std::vector<int>::push_back"
