from __future__ import annotations
import re
from rich.text import Text
from textual.widgets import Static
from ..utils.asm_help import ASM_INSTRUCTIONS
from ..utils.highlighter import INSTRUCTIONS

# User Palette
C_BG = "#EBEEEE"
C_TEXT = "#191A1A"
C_ACCENT1 = "#45d3ee" # Cyan
C_ACCENT2 = "#9FBFC5" # Muted Blue
C_ACCENT3 = "#94bfc1" # Teal
C_ACCENT4 = "#fecd91" # Orange

class InstructionHelpPanel(Static):
    """
    Floating popup showing description and examples for assembly instructions.
    """

    DEFAULT_CSS = f"""
    InstructionHelpPanel {{
        layer: overlay;
        dock: bottom;
        margin-left: 4;
        margin-right: 4;
        margin-bottom: 10; /* Positioned above the Source Peek */
        
        height: 3;
        width: 100%;
        
        background: {C_TEXT};
        color: {C_BG};
        border: solid {C_ACCENT1};
        padding: 0 1;
        display: none;
        opacity: 95%;
    }}
    """

    def show_for_asm_line(self, line_text: str) -> None:
        """
        Parse the instruction from the line and show its help text.
        """
        stripped = line_text.strip()
        if stripped.endswith(":") or not stripped:
            self.display = False
            return

        match = INSTRUCTIONS.search(stripped)
        mnemonic = match.group(0).upper() if match else None
        
        if not mnemonic:
            parts = stripped.split()
            if parts and not parts[0].startswith("."):
                mnemonic = parts[0].upper()
            else:
                self.display = False
                return

        help_data = None
        for key, data in ASM_INSTRUCTIONS.items():
            if mnemonic in key.split('/'):
                help_data = (key, data)
                break
            if mnemonic.startswith("B.") and key == "B.":
                help_data = (key, data)
                break
        
        if not help_data:
            self._render_unknown(mnemonic)
            return

        key, (desc, example, meaning) = help_data
        self._render_help(mnemonic, desc, example, meaning)
        self.display = True

    def _render_help(self, mnemonic: str, desc: str, example: str, meaning: str) -> None:
        text = Text()
        text.append(f" {mnemonic} ", style=f"bold {C_TEXT} on {C_ACCENT1}")
        text.append(f" {desc} ", style=f"bold {C_BG}")
        text.append(" │ ", style="dim")
        text.append(f"Example: {example} ", style=C_ACCENT4)
        text.append(" │ ", style="dim")
        text.append(meaning, style=f"italic {C_ACCENT3}")
        self.update(text)

    def _render_unknown(self, mnemonic: str) -> None:
        text = Text()
        text.append(f" {mnemonic} ", style=f"bold {C_TEXT} on {C_ACCENT1}")
        text.append(" No detailed help available for this instruction.", style="dim")
        self.update(text)
        self.display = True
