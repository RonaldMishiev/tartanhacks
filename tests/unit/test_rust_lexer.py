"""Unit tests for Rust-specific assembly lexer patterns."""
import pytest
from localbolt.parsing.rust_lexer import is_rust_noise_line, is_rust_noise_symbol


class TestRustNoiseLine:
    """Test Rust assembly noise line detection."""

    def test_rust_section(self):
        assert is_rust_noise_line("  .section .note.rustc")
        assert is_rust_noise_line("  .section .debug_info")

    def test_rust_labels(self):
        assert is_rust_noise_line("  .Ltmp0")
        assert is_rust_noise_line("  .Lfunc_begin0")
        assert is_rust_noise_line("  .LBB0_1")

    def test_normal_instruction_not_noise(self):
        assert not is_rust_noise_line("  mov rax, rbx")
        assert not is_rust_noise_line("  push rbp")

    def test_user_label_not_noise(self):
        assert not is_rust_noise_line("main:")
        assert not is_rust_noise_line("_ZN4test4mainE:")

    def test_text_section_not_noise(self):
        assert not is_rust_noise_line("  .section .text")


class TestRustNoiseSymbol:
    """Test Rust internal symbol detection."""

    def test_rust_alloc(self):
        assert is_rust_noise_symbol("__rust_alloc")
        assert is_rust_noise_symbol("__rust_dealloc")
        assert is_rust_noise_symbol("__rust_realloc")

    def test_rust_panic(self):
        assert is_rust_noise_symbol("core::panicking::panic")
        assert is_rust_noise_symbol("std::panicking::begin_panic")

    def test_user_symbol_not_noise(self):
        assert not is_rust_noise_symbol("example::main")
        assert not is_rust_noise_symbol("my_module::add")

    def test_cpp_symbol_not_noise(self):
        """Ensure C++ symbols don't match Rust noise patterns."""
        assert not is_rust_noise_symbol("std::vector<int>::push_back")
        assert not is_rust_noise_symbol("__cxa_throw")
