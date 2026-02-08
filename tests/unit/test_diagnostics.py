"""
Unit tests for diagnostics parsing.
Ensures both GCC/Clang and Rust compiler error formats are handled.
"""
import pytest
from localbolt.parsing.diagnostics import parse_diagnostics, Diagnostic


class TestParseDiagnosticsCpp:
    """Test parsing of GCC/Clang-style error output."""

    def test_single_error(self):
        stderr = "hello.cpp:10:5: error: expected ';' after expression"
        result = parse_diagnostics(stderr)
        assert len(result) == 1
        assert result[0].line == 10
        assert result[0].column == 5
        assert result[0].severity == "error"
        assert "expected ';'" in result[0].message

    def test_single_warning(self):
        stderr = "main.cpp:3:12: warning: unused variable 'x'"
        result = parse_diagnostics(stderr)
        assert len(result) == 1
        assert result[0].severity == "warning"
        assert result[0].line == 3

    def test_multiple_diagnostics(self):
        stderr = (
            "main.cpp:1:5: error: unknown type\n"
            "main.cpp:2:10: warning: implicit conversion\n"
            "main.cpp:5:1: error: expected '}'\n"
        )
        result = parse_diagnostics(stderr)
        assert len(result) == 3
        assert result[0].severity == "error"
        assert result[1].severity == "warning"
        assert result[2].severity == "error"

    def test_no_diagnostics(self):
        stderr = ""
        result = parse_diagnostics(stderr)
        assert result == []

    def test_noise_lines_ignored(self):
        """Lines that don't match the pattern should be skipped."""
        stderr = (
            "In file included from main.cpp:1:\n"
            "/usr/include/stdio.h:42:10: warning: something\n"
            "1 error generated.\n"
        )
        result = parse_diagnostics(stderr)
        # Only the stdio.h warning matches
        assert len(result) == 1
        assert result[0].severity == "warning"

    def test_full_path_filename(self):
        stderr = "/home/user/project/src/main.cpp:15:3: error: bad thing"
        result = parse_diagnostics(stderr)
        assert len(result) == 1
        assert result[0].line == 15
        assert result[0].column == 3


class TestParseDiagnosticsRust:
    """Test parsing of rustc-style error output.
    
    rustc format:   error[E0308]: mismatched types
                     --> src/main.rs:5:10
    
    This format does NOT match the GCC pattern, so we expect 0 results.
    This documents current behavior — Rust diagnostics may need a separate parser.
    """

    def test_rustc_errors_not_parsed_by_gcc_pattern(self):
        """rustc native format is not matched — documents the gap."""
        stderr = (
            "error[E0308]: mismatched types\n"
            " --> src/main.rs:5:10\n"
            "  |\n"
            "5 |     let x: i32 = \"hello\";\n"
            "  |                  ^^^^^^^ expected `i32`, found `&str`\n"
        )
        result = parse_diagnostics(stderr)
        # Current parser doesn't handle rustc format — this is expected
        assert len(result) == 0

    def test_rustc_with_gcc_style_line(self):
        """If rustc ever emits gcc-style lines, they should parse."""
        stderr = "main.rs:5:10: error: mismatched types"
        result = parse_diagnostics(stderr)
        assert len(result) == 1
        assert result[0].line == 5


class TestDiagnosticDataclass:
    """Test the Diagnostic dataclass itself."""

    def test_diagnostic_fields(self):
        d = Diagnostic(line=1, column=2, severity="error", message="bad")
        assert d.line == 1
        assert d.column == 2
        assert d.severity == "error"
        assert d.message == "bad"

    def test_diagnostic_equality(self):
        d1 = Diagnostic(line=1, column=2, severity="error", message="bad")
        d2 = Diagnostic(line=1, column=2, severity="error", message="bad")
        assert d1 == d2
