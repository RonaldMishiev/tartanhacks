"""
Source Peek Widget
==================
A small panel that displays the C++ source line corresponding to
whichever assembly line is currently under the cursor / scroll position.

This lives in its own file so it doesn't conflict with app.py or
the assembly view code.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from rich.text import Text
from textual.widgets import Static


class SourcePeekPanel(Static):
    """
    Bottom panel showing the C++ source line that maps to the current
    assembly region.

    The mapping comes from Member B's parser:
        asm_mapping: Dict[int, int]   — asm_line_idx -> source_line_number

    We also get the full source from the engine state:
        source_lines: List[str]       — the C++ file split by line
    """

    DEFAULT_CSS = """
    SourcePeekPanel {
        height: 5;
        dock: bottom;
        background: #252526;
        border-top: solid #3c3c3c;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._source_lines: List[str] = []
        self._asm_mapping: Dict[int, int] = {}
        self._current_source_line: Optional[int] = None

    # ── Public API ──────────────────────────────────────────

    def update_context(
        self,
        source_lines: List[str],
        asm_mapping: Dict[int, int],
    ) -> None:
        """
        Called whenever the engine produces new state.

        Args:
            source_lines: The C++ file content split into lines.
            asm_mapping:  { asm_line_index: source_line_number (1-based) }
        """
        self._source_lines = source_lines
        self._asm_mapping = asm_mapping

    def show_for_asm_line(self, asm_line: int) -> None:
        """
        Look up which C++ source line corresponds to the given assembly
        line number and display it.

        Args:
            asm_line: 1-based assembly line number.
        """
        src_num = self._asm_mapping.get(asm_line)

        # Walk backwards to find the nearest mapped source line
        if src_num is None:
            for offset in range(1, 20):
                src_num = self._asm_mapping.get(asm_line - offset)
                if src_num is not None:
                    break

        if src_num is None:
            self._current_source_line = None
            self._render_empty()
            return

        self._current_source_line = src_num
        self._render_line(src_num)

    # ── Internal rendering ──────────────────────────────────

    def _render_line(self, line_num: int) -> None:
        """Render a single C++ source line with its line number."""
        if not self._source_lines or line_num < 1 or line_num > len(self._source_lines):
            self._render_empty()
            return

        code = self._source_lines[line_num - 1]

        # Show surrounding context (1 line above and below)
        context = Text()
        if line_num >= 2:
            prev = self._source_lines[line_num - 2]
            context.append(f"  {line_num - 1:>4} │ ", style="dim")
            context.append(prev, style="dim")
            context.append("\n")

        context.append(f"► {line_num:>4} │ ", style="bold yellow")
        context.append(code, style="bold white")
        context.append("\n")

        if line_num < len(self._source_lines):
            nxt = self._source_lines[line_num]
            context.append(f"  {line_num + 1:>4} │ ", style="dim")
            context.append(nxt, style="dim")

        self.update(context)

    def _render_empty(self) -> None:
        """Show placeholder when no mapping is available."""
        t = Text()
        t.append("C++ ", style="bold cyan")
        t.append("│ ", style="dim")
        t.append("(hover over assembly to see source)", style="dim italic")
        self.update(t)
