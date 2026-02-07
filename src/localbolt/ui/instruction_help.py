"""
Instruction Help Widget
=======================
A panel that displays the description and example for the assembly
instruction currently under the cursor.
"""

from __future__ import annotations
import re
from rich.text import Text
from textual.widgets import Static
from ..utils.asm_help import ASM_INSTRUCTIONS
from ..utils.highlighter import INSTRUCTIONS

class InstructionHelpPanel(Static):
    """
    Panel showing description and examples for assembly instructions.
    """

    DEFAULT_CSS = """
    InstructionHelpPanel {
        width: 40;
        height: 1fr;
        background: #191A1A;
        padding: 1 1;
        color: #EBEEEE;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_instr = None

    def show_for_asm_line(self, line_text: str) -> None:
        """
        Parse the instruction from the line and show its help text.
        """
        stripped = line_text.strip()
        
        # If it's a label, don't try to show instruction help
        if stripped.endswith(":") or not stripped:
            self._render_empty()
            return

        # Extract the mnemonic (first word that looks like an instruction)
        match = INSTRUCTIONS.search(stripped)
        if match:
            mnemonic = match.group(0).upper()
        else:
            # Fallback: try the first word if it's not a directive
            parts = stripped.split()
            if parts and not parts[0].startswith("."):
                mnemonic = parts[0].upper()
            else:
                self._render_empty()
                return

        # Handle variants like JNE/JNZ or ARM conditional branches (B.EQ, B.NE)
        help_data = None
        for key, data in ASM_INSTRUCTIONS.items():
            # Check for exact match in slash-separated keys
            if mnemonic in key.split('/'):
                help_data = (key, data)
                break
            # Handle ARM conditional branches matching "B."
            if mnemonic.startswith("B.") and key == "B.":
                help_data = (key, data)
                break
        
        if not help_data:
            # Check for "starts with" to catch variants like MOVSX -> MOV or B.EQ -> B.
            for key, data in ASM_INSTRUCTIONS.items():
                primary_key = key.split('/')[0]
                if mnemonic.startswith(primary_key) and len(primary_key) >= 2:
                    help_data = (key, data)
                    break

        if not help_data:
            self._render_unknown(mnemonic)
            return

        key, (desc, example, meaning) = help_data
        self._render_help(mnemonic, desc, example, meaning)

    def _render_help(self, mnemonic: str, desc: str, example: str, meaning: str) -> None:
        text = Text()
        text.append(f" {mnemonic} ", style="bold on #45d3ee #191A1A")
        text.append(" ")
        text.append(desc, style="#EBEEEE")
        text.append("\n\n")
        text.append("  Example: ", style="bold #fecd91")
        text.append(example, style="#fecd91")
        text.append("  │  ", style="dim")
        text.append(meaning, style="italic #94bfc1")
        self.update(text)

    def _render_unknown(self, mnemonic: str) -> None:
        text = Text()
        text.append(f" {mnemonic} ", style="bold on #45d3ee #191A1A")
        text.append(" ")
        text.append("No detailed help available for this instruction.", style="dim")
        self.update(text)

    def _render_empty(self) -> None:
        text = Text()
        text.append("ASM ", style="bold #45d3ee")
        text.append("│ ", style="dim")
        text.append("(move cursor to an instruction to see help)", style="dim italic")
        self.update(text)
