"""
Floating Source Peek Widget
"""

from __future__ import annotations
from typing import Dict, List, Optional
from rich.text import Text
from textual.widgets import Static

# User Palette
C_BG = "#EBEEEE"
C_TEXT = "#191A1A"
C_ACCENT1 = "#45d3ee" # Cyan
C_ACCENT2 = "#9FBFC5" # Muted Blue
C_ACCENT3 = "#94bfc1" # Teal
C_ACCENT4 = "#fecd91" # Orange

class SourcePeekPanel(Static):
    """
    Floating popup showing C++ source line with context.
    Designed to float over the main content.
    """

    DEFAULT_CSS = f"""
    SourcePeekPanel {{
        layer: overlay;
        /* Positioning: Bottom Right corner by default */
        dock: bottom;
        margin-left: 4;
        margin-right: 4;
        margin-bottom: 3;
        
        width: 100%;
        height: auto;
        
        background: {C_TEXT};
        color: {C_BG};
        border: solid {C_ACCENT3};
        padding: 0 1;
        display: none;
        opacity: 95%; 
    }}
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._source_lines: List[str] = []
        self._asm_mapping: Dict[int, int] = {}

    def update_context(self, source_lines: List[str], asm_mapping: Dict[int, int]) -> None:
        self._source_lines = source_lines
        self._asm_mapping = asm_mapping

    def show_for_asm_line(self, asm_line: int) -> None:
        src_num = self._asm_mapping.get(asm_line)
        
        # Backward search for nearest mapped line
        if src_num is None:
            for offset in range(1, 20):
                if asm_line - offset < 0: break
                src_num = self._asm_mapping.get(asm_line - offset)
                if src_num is not None: break

        if src_num is None:
            self.display = False
            return

        self.display = True
        self._render_line(src_num)

    def _render_line(self, line_num: int) -> None:
        """Renders target line with 1 line of context above and below."""
        if not self._source_lines or line_num < 1 or line_num > len(self._source_lines):
            self.display = False
            return

        text = Text()
        text.append(" C++ SOURCE ", style=f"bold {C_TEXT} on {C_ACCENT3}")
        text.append("\n")

        # 1. Line Above
        if line_num >= 2:
            prev = self._source_lines[line_num - 2]
            text.append(f" {line_num - 1:>4} │ ", style=f"dim {C_BG}")
            text.append(prev, style=f"dim {C_BG}")
            text.append("\n")

        # 2. TARGET LINE
        code = self._source_lines[line_num - 1]
        text.append(f"►{line_num:>4} │ ", style=f"bold {C_ACCENT4}")
        text.append(code, style=f"bold {C_BG} on {C_ACCENT2}")
        text.append("\n")

        # 3. Line Below
        if line_num < len(self._source_lines):
            nxt = self._source_lines[line_num]
            text.append(f" {line_num + 1:>4} │ ", style=f"dim {C_BG}")
            text.append(nxt, style=f"dim {C_BG}")

        self.update(text)
