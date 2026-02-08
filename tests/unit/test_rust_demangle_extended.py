"""
Extended edge case tests for Rust demangling.
Covers: llvm-cxxfilt fallback, exception paths, multiline input,
and edge cases in simplify_rust_symbols.
"""
import pytest
from unittest.mock import patch, MagicMock
from localbolt.parsing.rust_demangle import (
    demangle_rust,
    simplify_rust_symbols,
    has_rustfilt,
    RE_RUST_HASH,
)


class TestDemangleRustFallbacks:
    """Test the full fallback chain: rustfilt -> llvm-cxxfilt -> warn."""

    def test_llvm_cxxfilt_fallback(self):
        """When rustfilt is missing but llvm-cxxfilt exists, use it."""
        def which_side_effect(tool):
            if tool == "rustfilt":
                return None
            if tool == "llvm-cxxfilt":
                return "/usr/bin/llvm-cxxfilt"
            return None

        with patch("localbolt.parsing.rust_demangle.shutil.which", side_effect=which_side_effect):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="test::main\n")
                result = demangle_rust("_ZN4test4mainE")
                assert "test::main" in result

    def test_llvm_cxxfilt_error_returns_original(self):
        """If llvm-cxxfilt fails, return original text."""
        def which_side_effect(tool):
            if tool == "rustfilt":
                return None
            if tool == "llvm-cxxfilt":
                return "/usr/bin/llvm-cxxfilt"
            return None

        with patch("localbolt.parsing.rust_demangle.shutil.which", side_effect=which_side_effect):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="")
                original = "_ZN4test4mainE"
                result = demangle_rust(original)
                assert result == original

    def test_llvm_cxxfilt_exception_returns_original(self):
        """If llvm-cxxfilt throws an exception, return original text."""
        def which_side_effect(tool):
            if tool == "rustfilt":
                return None
            if tool == "llvm-cxxfilt":
                return "/usr/bin/llvm-cxxfilt"
            return None

        with patch("localbolt.parsing.rust_demangle.shutil.which", side_effect=which_side_effect):
            with patch("subprocess.run", side_effect=OSError("boom")):
                original = "_ZN4test4mainE"
                result = demangle_rust(original)
                assert result == original

    def test_rustfilt_exception_returns_error_msg(self):
        """If Popen throws, return error message with original text."""
        with patch("localbolt.parsing.rust_demangle.shutil.which", return_value="/usr/bin/rustfilt"):
            with patch("subprocess.Popen", side_effect=OSError("no such file")):
                result = demangle_rust("_ZN4test4mainE")
                assert "Error" in result
                assert "_ZN4test4mainE" in result


class TestDemangleRustEdgeCases:
    """Edge cases for demangle_rust."""

    def test_empty_input(self):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0

        with patch("localbolt.parsing.rust_demangle.shutil.which", return_value="/usr/bin/rustfilt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_rust("")
                assert isinstance(result, str)

    def test_multiline_input(self):
        """Should handle assembly with multiple mangled symbols."""
        input_text = (
            "_ZN4test4mainE:\n"
            "  push rbp\n"
            "  call _ZN4test3addE\n"
        )
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            "test::main:\n  push rbp\n  call test::add\n", ""
        )
        mock_proc.returncode = 0

        with patch("localbolt.parsing.rust_demangle.shutil.which", return_value="/usr/bin/rustfilt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_rust(input_text)
                assert "test::main" in result
                assert "test::add" in result

    def test_plain_text_passthrough(self):
        """Non-mangled text should pass through unchanged."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("push rbp\nret\n", "")
        mock_proc.returncode = 0

        with patch("localbolt.parsing.rust_demangle.shutil.which", return_value="/usr/bin/rustfilt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_rust("push rbp\nret\n")
                assert "push rbp" in result


class TestSimplifyRustSymbolsExtended:
    """Extended edge cases for simplify_rust_symbols."""

    def test_multiple_hashes_on_same_line(self):
        """Multiple hash suffixes in the same text should all be removed."""
        text = "call foo::h1234567890abcdef\ncall bar::habcdef1234567890"
        result = simplify_rust_symbols(text)
        assert "::h1234567890abcdef" not in result
        assert "::habcdef1234567890" not in result
        assert "call foo" in result
        assert "call bar" in result

    def test_hash_not_16_chars_preserved(self):
        """Hash suffixes with wrong length should NOT be removed."""
        text = "foo::h1234"  # Only 4 hex chars, not 16
        result = simplify_rust_symbols(text)
        assert "::h1234" in result

    def test_shortens_fn_once(self):
        result = simplify_rust_symbols("core::ops::function::FnOnce::call_once")
        assert result == "FnOnce::call_once"

    def test_shortens_fn_mut(self):
        result = simplify_rust_symbols("core::ops::function::FnMut::call_mut")
        assert result == "FnMut::call_mut"

    def test_empty_string(self):
        assert simplify_rust_symbols("") == ""

    def test_no_rust_content(self):
        """C++ assembly should pass through untouched."""
        text = "call std::vector<int>::push_back"
        assert simplify_rust_symbols(text) == text

    def test_combined_simplification(self):
        """Test hash removal + path shortening together."""
        text = "alloc::vec::Vec<i32>::push::h1234567890abcdef"
        result = simplify_rust_symbols(text)
        assert result == "Vec<i32>::push"


class TestRustHashRegex:
    """Directly test the RE_RUST_HASH pattern."""

    def test_matches_16_hex_digits(self):
        assert RE_RUST_HASH.search("foo::h1234567890abcdef")

    def test_no_match_short_hash(self):
        assert not RE_RUST_HASH.search("foo::h1234")

    def test_no_match_uppercase(self):
        """Hash should be lowercase hex only."""
        assert not RE_RUST_HASH.search("foo::hABCDEF1234567890")

    def test_no_match_no_prefix(self):
        assert not RE_RUST_HASH.search("h1234567890abcdef")
