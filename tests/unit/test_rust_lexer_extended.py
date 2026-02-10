"""
Extended edge case tests for Rust-specific assembly lexer patterns.
"""
import pytest
from localbolt.parsing.rust_lexer import (
    is_rust_noise_line,
    is_rust_noise_symbol,
    RE_RUST_INTERNAL,
    RE_RUST_PANIC,
    RE_RUST_LABELS,
    RE_RUST_SECTIONS,
)


class TestRustNoiseLineEdgeCases:
    """Edge cases for is_rust_noise_line."""

    def test_empty_string(self):
        assert not is_rust_noise_line("")

    def test_whitespace_only(self):
        assert not is_rust_noise_line("    ")

    def test_comment_section(self):
        assert is_rust_noise_line("  .section .comment")

    def test_note_gnu(self):
        assert is_rust_noise_line("  .section .note.gnu.build-id")

    def test_debug_underscore_variants(self):
        """All .debug_* sections should be noise."""
        assert is_rust_noise_line("  .section .debug_line")
        assert is_rust_noise_line("  .section .debug_abbrev")
        assert is_rust_noise_line("  .section .debug_str")

    def test_lfunc_end(self):
        assert is_rust_noise_line("  .Lfunc_end0")

    def test_lbb_with_underscore(self):
        assert is_rust_noise_line("  .LBB0_1")

    def test_data_section_not_noise(self):
        assert not is_rust_noise_line("  .section .data")

    def test_instruction_with_label_ref_not_noise(self):
        """An instruction referencing a .LBB label should NOT be noise."""
        assert not is_rust_noise_line("  jne .LBB0_1")

    def test_globl_not_noise(self):
        assert not is_rust_noise_line("  .globl main")


class TestRustNoiseSymbolEdgeCases:
    """Edge cases for is_rust_noise_symbol."""

    def test_empty_string(self):
        assert not is_rust_noise_symbol("")

    def test_rust_alloc_zeroed(self):
        assert is_rust_noise_symbol("__rust_alloc_zeroed")

    def test_rust_alloc_error_handler(self):
        assert is_rust_noise_symbol("__rust_alloc_error_handler")

    def test_rdl_prefix(self):
        assert is_rust_noise_symbol("__rdl_alloc")

    def test_rg_prefix(self):
        assert is_rust_noise_symbol("__rg_oom")

    def test_rust_begin_unwind(self):
        assert is_rust_noise_symbol("rust_begin_unwind")

    def test_core_panic_variant(self):
        assert is_rust_noise_symbol("core::panic::panic_fmt")

    def test_user_function_with_rust_prefix(self):
        """A user function named 'my_rust_allocator' should NOT be noise."""
        assert not is_rust_noise_symbol("my_rust_allocator")

    def test_partial_match_not_noise(self):
        """'rust_alloc' without the double underscore prefix should NOT match."""
        # The regex requires __rust_alloc
        assert not is_rust_noise_symbol("rust_alloc")

    def test_std_collections_not_noise(self):
        """Standard library collection types are NOT noise (they're user-relevant)."""
        assert not is_rust_noise_symbol("std::collections::HashMap")
        assert not is_rust_noise_symbol("std::vec::Vec")

    def test_core_iter_not_noise(self):
        assert not is_rust_noise_symbol("core::iter::Iterator")


class TestRustRegexPatterns:
    """Directly test the compiled regex patterns."""

    def test_internal_pattern_matches(self):
        assert RE_RUST_INTERNAL.search("__rust_alloc")
        assert RE_RUST_INTERNAL.search("__rust_dealloc")
        assert RE_RUST_INTERNAL.search("__rust_realloc")
        assert RE_RUST_INTERNAL.search("__rdl_oom")
        assert RE_RUST_INTERNAL.search("__rg_oom")

    def test_internal_pattern_no_match(self):
        assert not RE_RUST_INTERNAL.search("malloc")
        assert not RE_RUST_INTERNAL.search("free")

    def test_panic_pattern_matches(self):
        assert RE_RUST_PANIC.search("core::panicking::panic")
        assert RE_RUST_PANIC.search("std::panicking::try")
        assert RE_RUST_PANIC.search("rust_begin_unwind")

    def test_panic_pattern_no_match(self):
        assert not RE_RUST_PANIC.search("user::panic_handler")
        # The word "panic" alone in a user function shouldn't match
        # because the regex requires core::panicking or std::panicking
        assert not RE_RUST_PANIC.search("my_module::handle_panic_result")

    def test_labels_pattern(self):
        assert RE_RUST_LABELS.match("  .Ltmp0")
        assert RE_RUST_LABELS.match("  .Ltmp99")
        assert RE_RUST_LABELS.match("  .LBB0")
        assert not RE_RUST_LABELS.match("  mov rax, rbx")

    def test_sections_pattern(self):
        assert RE_RUST_SECTIONS.search(".note.rustc")
        assert RE_RUST_SECTIONS.search(".note.gnu.build-id")
        assert RE_RUST_SECTIONS.search(".debug_info")
        assert not RE_RUST_SECTIONS.search(".text")
        assert not RE_RUST_SECTIONS.search(".data")
