"""
Extended tests for the assembly lexer (lexer.py).
Covers edge cases for clean_assembly_with_mapping to ensure
the Rust changes don't break C++ assembly cleaning.
"""
import pytest
import os
from localbolt.parsing.lexer import clean_assembly_with_mapping


class TestLexerEmptyInput:
    """Edge cases with empty or minimal input."""

    def test_empty_string(self):
        cleaned, mapping = clean_assembly_with_mapping("")
        assert cleaned == ""
        assert mapping == {}

    def test_whitespace_only(self):
        cleaned, mapping = clean_assembly_with_mapping("   \n   \n   ")
        assert cleaned == ""
        assert mapping == {}

    def test_single_instruction(self):
        asm = """
    .file 1 "test.cpp"
    .text
    .loc 1 1 0
    pushq %rbp
"""
        cleaned, mapping = clean_assembly_with_mapping(asm, "test.cpp")
        assert "pushq" in cleaned


class TestLexerDirectiveFiltering:
    """Ensure directives are properly filtered."""

    def test_cfi_directives_removed(self):
        asm = """
    .file 1 "test.cpp"
    .text
main:
    .cfi_startproc
    .cfi_def_cfa_offset 16
    .loc 1 1 0
    pushq %rbp
    .cfi_endproc
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".cfi_startproc" not in cleaned
        assert ".cfi_def_cfa_offset" not in cleaned
        assert ".cfi_endproc" not in cleaned
        assert "pushq" in cleaned

    def test_loc_directives_removed(self):
        asm = """
    .file 1 "test.cpp"
    .loc 1 5 0
    pushq %rbp
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".loc" not in cleaned

    def test_file_directives_removed(self):
        asm = """
    .file 1 "test.cpp"
    .file 2 "/usr/include/stdio.h"
    .text
    .loc 1 1 0
    pushq %rbp
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".file" not in cleaned

    def test_endbr64_removed(self):
        asm = """
    .file 1 "test.cpp"
    .text
main:
    .loc 1 1 0
    endbr64
    pushq %rbp
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert "endbr64" not in cleaned
        assert "pushq" in cleaned


class TestLexerSectionFiltering:
    """Test section-based filtering."""

    def test_debug_section_filtered(self):
        asm = """
    .file 1 "test.cpp"
    .text
    .loc 1 1 0
    pushq %rbp
    .section .debug_info
    .long 42
    .section .text
    .loc 1 2 0
    ret
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".long" not in cleaned
        assert ".debug" not in cleaned
        assert "pushq" in cleaned
        assert "ret" in cleaned

    def test_dwarf_section_filtered(self):
        asm = """
    .file 1 "test.cpp"
    .text
    .loc 1 1 0
    pushq %rbp
    .section __DWARF,__debug_info
    .byte 0x1
    .section __TEXT,__text
    .loc 1 2 0
    ret
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".byte" not in cleaned


class TestLexerLabelHandling:
    """Test label processing."""

    def test_noise_labels_removed(self):
        asm = """
    .file 1 "test.cpp"
    .text
.LFB0:
    .loc 1 1 0
    pushq %rbp
.LFE0:
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".LFB0:" not in cleaned
        assert ".LFE0:" not in cleaned

    def test_user_label_preserved(self):
        asm = """
    .file 1 "test.cpp"
    .text
_Z3foov:
    .loc 1 1 0
    pushq %rbp
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        # Label should be there (possibly with underscore stripped on macOS)
        assert "foov:" in cleaned or "Z3foov:" in cleaned

    def test_system_symbol_block_filtered(self):
        asm = """
    .file 1 "test.cpp"
    .text
_Z3foov:
    .loc 1 1 0
    pushq %rbp
___cxa_atexit:
    .loc 1 100 0
    movl $0, %eax
_Z3barv:
    .loc 1 5 0
    ret
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        # System symbol block should be filtered
        assert "___cxa_atexit" not in cleaned
        # But user functions should remain
        assert "pushq" in cleaned
        assert "ret" in cleaned


class TestLexerSourceMapping:
    """Test source line mapping accuracy."""

    def test_mapping_accuracy(self):
        asm = """
    .file 1 "test.cpp"
    .text
main:
    .loc 1 10 0
    pushq %rbp
    .loc 1 11 0
    movq %rsp, %rbp
    popq %rbp
    .loc 1 12 0
    ret
"""
        cleaned, mapping = clean_assembly_with_mapping(asm, "test.cpp")
        lines = cleaned.splitlines()

        # Verify some mapping entries exist
        assert len(mapping) > 0

        # All mapped source lines should be in {10, 11, 12}
        for src_line in mapping.values():
            assert src_line in {10, 11, 12}

    def test_no_source_filename_still_works(self):
        """When source_filename is None, should still produce output."""
        asm = """
    .file 1 "test.cpp"
    .text
    .loc 1 1 0
    pushq %rbp
"""
        cleaned, mapping = clean_assembly_with_mapping(asm, None)
        assert isinstance(cleaned, str)
        assert isinstance(mapping, dict)

    def test_multi_file_filtering(self):
        """Instructions from non-source files should be filtered."""
        asm = """
    .file 1 "main.cpp"
    .file 2 "/usr/include/iostream"
    .text
main:
    .loc 1 5 0
    pushq %rbp
    .loc 2 500 0
    movl $42, %eax
    .loc 1 6 0
    ret
"""
        cleaned, mapping = clean_assembly_with_mapping(asm, "main.cpp")
        assert "pushq" in cleaned
        assert "ret" in cleaned
        # The iostream instruction should be filtered
        assert "$42" not in cleaned
        assert 500 not in mapping.values()


class TestLexerDataDirectives:
    """Test handling of data directives (.asciz, .string)."""

    def test_asciz_preserved(self):
        asm = """
    .file 1 "test.cpp"
    .text
main:
    .loc 1 1 0
    .asciz "hello"
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".asciz" in cleaned or "hello" in cleaned

    def test_string_preserved(self):
        asm = """
    .file 1 "test.cpp"
    .text
main:
    .loc 1 1 0
    .string "world"
"""
        cleaned, _ = clean_assembly_with_mapping(asm, "test.cpp")
        assert ".string" in cleaned or "world" in cleaned
