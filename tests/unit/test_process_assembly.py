"""
Unit tests for the process_assembly pipeline — ensures the language routing
works correctly and does NOT break existing C++ behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from localbolt.parsing import process_assembly, simplify_symbols


# ────────────────────────────────────────────────────────────
# Test simplify_symbols (C++ path) — never had direct tests
# ────────────────────────────────────────────────────────────
class TestSimplifySymbolsCpp:
    """Direct tests for the C++ simplify_symbols function."""

    def test_removes_stl_versioning(self):
        assert simplify_symbols("std::__1::vector") == "std::vector"
        assert simplify_symbols("std::__2::string") == "std::string"

    def test_removes_abi_tags(self):
        assert simplify_symbols("foo[abi:cxx11]") == "foo"
        assert simplify_symbols("bar[abi:v160]") == "bar"

    def test_removes_both(self):
        result = simplify_symbols("std::__1::basic_string[abi:cxx11]")
        assert result == "std::basic_string"

    def test_passthrough_plain_text(self):
        assert simplify_symbols("push rbp") == "push rbp"
        assert simplify_symbols("mov rax, rbx") == "mov rax, rbx"

    def test_passthrough_empty_string(self):
        assert simplify_symbols("") == ""

    def test_passthrough_rust_symbols(self):
        """C++ simplifier should NOT mangle Rust symbols."""
        result = simplify_symbols("example::main::h1a2b3c4d5e6f7a8b")
        assert "example::main" in result

    def test_multiple_abi_tags(self):
        result = simplify_symbols("foo[abi:cxx11][abi:v160]")
        assert result == "foo"


# ────────────────────────────────────────────────────────────
# Test process_assembly language routing
# ────────────────────────────────────────────────────────────
MINIMAL_CPP_ASM = """\
    .file 1 "test.cpp"
    .text
_Z3foov:
    .loc 1 5 0
    pushq %rbp
    ret
"""

MINIMAL_RUST_ASM = """\
    .file 1 "test.rs"
    .text
_ZN4test4main17h1234567890abcdefE:
    .loc 1 5 0
    pushq %rbp
    ret
"""


class TestProcessAssemblyRouting:
    """Verify that language parameter routes to correct demangler/simplifier."""

    def test_returns_three_values(self):
        """process_assembly always returns a 3-tuple."""
        result = process_assembly(MINIMAL_CPP_ASM, "test.cpp")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_returns_three_values_rust(self):
        result = process_assembly(MINIMAL_RUST_ASM, "test.rs", language="rust")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_default_language_is_cpp(self):
        """When language is omitted, it defaults to C++ — existing behavior preserved."""
        with patch("localbolt.parsing.demangle_stream") as mock_cpp:
            with patch("localbolt.parsing.demangle_rust") as mock_rust:
                mock_cpp.return_value = "demangled"
                mock_rust.return_value = "demangled"
                process_assembly(MINIMAL_CPP_ASM, "test.cpp")
                mock_cpp.assert_called_once()
                mock_rust.assert_not_called()

    def test_rust_language_uses_rust_demangler(self):
        """When language='rust', it uses demangle_rust, not demangle_stream."""
        with patch("localbolt.parsing.demangle_stream") as mock_cpp:
            with patch("localbolt.parsing.demangle_rust") as mock_rust:
                mock_cpp.return_value = "demangled"
                mock_rust.return_value = "demangled"
                process_assembly(MINIMAL_RUST_ASM, "test.rs", language="rust")
                mock_rust.assert_called_once()
                mock_cpp.assert_not_called()

    def test_cpp_language_explicit(self):
        """Explicitly passing language='cpp' is the same as default."""
        with patch("localbolt.parsing.demangle_stream") as mock_cpp:
            mock_cpp.return_value = "demangled"
            process_assembly(MINIMAL_CPP_ASM, "test.cpp", language="cpp")
            mock_cpp.assert_called_once()

    def test_mangled_asm_unchanged(self):
        """The third return value (mangled_asm) should be the cleaned but NOT demangled text."""
        _, _, mangled = process_assembly(MINIMAL_CPP_ASM, "test.cpp")
        # Should contain the raw (cleaned) assembly — directives stripped but symbols still mangled
        assert "pushq" in mangled or "push" in mangled

    def test_empty_asm_input(self):
        """Empty assembly input should not crash."""
        result, mapping, mangled = process_assembly("", "test.cpp")
        assert isinstance(result, str)
        assert isinstance(mapping, dict)
        assert isinstance(mangled, str)

    def test_no_source_filename(self):
        """Omitting source_filename should not crash (uses default file ID)."""
        result, mapping, mangled = process_assembly(MINIMAL_CPP_ASM)
        assert isinstance(result, str)
