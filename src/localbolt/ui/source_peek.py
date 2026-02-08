"""
Floating Source Peek Widget
"""

from __future__ import annotations
from typing import Dict, List, Optional
from rich.text import Text
from textual.widgets import Static
from ..utils.lang import detect_language, source_label, Language

# User Palette
C_BG = "#EBEEEE"
C_TEXT = "#191A1A"
C_ACCENT1 = "#007b9a" # Strong Cyan
C_ACCENT2 = "#9FBFC5" # Muted Blue-Grey
C_ACCENT3 = "#00796b" # Strong Teal
C_ACCENT4 = "#af5f00" # Strong Orange

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
        
        background: {C_BG};
        color: {C_TEXT};
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
        self._language: Language = Language.CPP

    def update_context(self, source_lines: List[str], asm_mapping: Dict[int, int], source_path: str = "") -> None:
        self._source_lines = source_lines
        self._asm_mapping = asm_mapping
        if source_path:
            self._language = detect_language(source_path)

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
        label = source_label(self._language)
        text.append(f" {label} ", style=f"bold {C_BG} on {C_ACCENT3}")
        text.append("\n")

        # 1. Line Above
        if line_num >= 2:
            prev = self._source_lines[line_num - 2]
            text.append(f" {line_num - 1:>4} │ ", style=f"dim {C_TEXT}")
            text.append(prev, style=f"dim {C_TEXT}")
            text.append("\n")

        # 2. TARGET LINE
        code = self._source_lines[line_num - 1]
        text.append(f"►{line_num:>4} │ ", style=f"bold {C_ACCENT4}")
        text.append(code, style=f"bold {C_TEXT} on {C_ACCENT2}")
        text.append("\n")

        # 3. Line Below
        if line_num < len(self._source_lines):
            nxt = self._source_lines[line_num]
            text.append(f" {line_num + 1:>4} │ ", style=f"dim {C_TEXT}")
            text.append(nxt, style=f"dim {C_TEXT}")

        self.update(text)
