"""
Tests for the SourcePeekPanel — ensures the Rust label rendering
works correctly and doesn't break C++ label rendering.
"""
import pytest
from localbolt.ui.source_peek import SourcePeekPanel
from localbolt.utils.lang import Language


class TestSourcePeekLanguage:
    """Test language-aware behavior of SourcePeekPanel."""

    def test_default_language_is_cpp(self):
        panel = SourcePeekPanel()
        assert panel._language == Language.CPP

    def test_update_context_detects_cpp(self):
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["int main() {}"],
            asm_mapping={0: 1},
            source_path="/home/user/main.cpp",
        )
        assert panel._language == Language.CPP

    def test_update_context_detects_rust(self):
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["fn main() {}"],
            asm_mapping={0: 1},
            source_path="/home/user/main.rs",
        )
        assert panel._language == Language.RUST

    def test_update_context_no_path_keeps_default(self):
        """When source_path is empty, language stays at default (CPP)."""
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["int main() {}"],
            asm_mapping={0: 1},
            source_path="",
        )
        assert panel._language == Language.CPP

    def test_update_context_no_path_kwarg_keeps_default(self):
        """When source_path is omitted, language stays at default (CPP)."""
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["int main() {}"],
            asm_mapping={0: 1},
        )
        assert panel._language == Language.CPP


class TestSourcePeekMapping:
    """Test show_for_asm_line logic."""

    def test_show_for_mapped_line(self):
        """Mapped line should trigger _render_line (mocked to avoid Textual context)."""
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["line1", "line2", "line3"],
            asm_mapping={0: 1, 1: 2, 2: 3},
        )
        # Mock _render_line to avoid Textual app context requirement
        from unittest.mock import MagicMock
        panel._render_line = MagicMock()
        panel.show_for_asm_line(0)
        panel._render_line.assert_called_once_with(1)

    def test_show_for_unmapped_line_backward_search(self):
        """Should search backward for nearest mapped line."""
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["line1", "line2", "line3"],
            asm_mapping={0: 1},
        )
        from unittest.mock import MagicMock
        panel._render_line = MagicMock()
        # Line 5 is not mapped, should search backward and find line 0 -> source 1
        panel.show_for_asm_line(5)
        panel._render_line.assert_called_once_with(1)

    def test_show_for_negative_line(self):
        """Should not crash with negative line numbers."""
        panel = SourcePeekPanel()
        panel.update_context(
            source_lines=["line1"],
            asm_mapping={},
        )
        panel.show_for_asm_line(-1)

    def test_update_context_stores_lines(self):
        panel = SourcePeekPanel()
        lines = ["int main() {", "  return 0;", "}"]
        mapping = {0: 1, 1: 2, 2: 3}
        panel.update_context(lines, mapping)
        assert panel._source_lines == lines
        assert panel._asm_mapping == mapping

    def test_empty_source_lines(self):
        panel = SourcePeekPanel()
        panel.update_context([], {})
        panel.show_for_asm_line(0)
        # Should not crash, just hide
