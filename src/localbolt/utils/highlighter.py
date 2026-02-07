import re
import shutil
from rich.text import Text

# Palette provided by user
C_FOREGROUND = "#EBEEEE"
C_TEXT = "#191A1A"
C_MISC1 = "#9FBFC5" # Muted Blue-Grey
C_MISC2 = "#45d3ee" # Bright Cyan
C_MISC3 = "#94bfc1" # Pale Teal
C_MISC4 = "#fecd91" # Pale Orange

REGISTERS = re.compile(
    r"\b("
    r"r[abcd]x|r[sd]i|r[bs]p|r(?:8|9|1[0-5])[dwb]?"
    r"|e[abcd]x|e[sd]i|e[bs]p"
    r"|[abcd][hl]|[abcd]x|[sd]il?|[bs]pl?"
    r"|xmm[0-9]+|ymm[0-9]+|zmm[0-9]+"
    r"|[wx][0-9]{1,2}|sp|fp|lr"
    r")\b",
    re.IGNORECASE,
)

SIZE_KEYWORDS = re.compile(r"\b(DWORD|QWORD|WORD|BYTE|PTR)\b")
NUMBERS = re.compile(r"\b(0x[0-9a-fA-F]+|0b[01]+|[0-9]+)\b")
INSTRUCTIONS = re.compile(
    r"\b("
    r"movs?[xzbw]?|lea|add|sub|imul|idiv|mul|div|inc|dec"
    r"|cmp|test|and|or|xor|not|shl|shr|sar|sal"
    r"|jmp|je|jne|jz|jnz|jg|jge|jl|jle|ja|jae|jb|jbe"
    r"|call|ret|push|pop|nop|int|syscall|leave|enter"
    r"|cmov\w+|stp|ldp|stur|ldur|adrp|bl|b\."
    r")\b",
    re.IGNORECASE,
)

def _severity_styles(cycles: int | None) -> tuple[str, str]:
    """Light-mode compatible heatmap palette."""
    if cycles is None: return (C_TEXT, f"on {C_FOREGROUND}")
    # Low: Pale green
    if cycles <= 1: return (C_TEXT, "on #d1e7dd")
    # Med: Pale amber
    if cycles <= 4: return (C_TEXT, "on #fff3cd")
    # High: Pale red
    return (C_TEXT, "on #f8d7da")

def _highlight_asm_line(line: str, bg: str) -> Text:
    segment = Text()
    stripped = line.lstrip()
    if stripped.startswith("#") or stripped.startswith(";"):
        segment.append(line, style=f"italic #888888 {bg}")
        return segment

    token_styles: list[str | None] = [None] * len(line)
    
    # Apply Palette
    label_match = re.match(r"^(\s*\.?\w+\s*:)", line)
    if label_match:
        for j in range(label_match.start(), label_match.end()):
            token_styles[j] = f"bold {C_MISC3}" # Teal Labels

    for m in INSTRUCTIONS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = f"bold {C_MISC2}" # Cyan Instructions

    for m in SIZE_KEYWORDS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "#a37acc" # Muted Purple

    for m in NUMBERS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "#666666"

    for m in REGISTERS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = f"bold {C_MISC4}" # Orange Registers

    i = 0
    while i < len(line):
        cur_style = token_styles[i]
        j = i
        while j < len(line) and token_styles[j] == cur_style:
            j += 1
        full_style = f"{cur_style} {bg}" if cur_style else f"{C_TEXT} {bg}"
        segment.append(line[i:j], style=full_style.strip())
        i = j
    return segment

def build_gutter(asm_lines: list[str], cycle_counts: dict[int, int], width: int = 150) -> Text:
    gutter_width = 6
    result = Text(no_wrap=True)
    for i, line in enumerate(asm_lines):
        line_num = i + 1
        cycles = cycle_counts.get(line_num)
        fg_style, bg = _severity_styles(cycles)
        result.append_text(_highlight_asm_line(line, bg))
        padding_needed = max(1, width - len(line) - gutter_width)
        result.append(" " * padding_needed, style=bg.strip() or None)
        if cycles is not None:
            result.append(f"{cycles:>{gutter_width}}c", style=f"bold {C_TEXT} {bg}".strip())
        else:
            result.append(" " * (gutter_width + 1), style=bg.strip() or None)
        if line_num < len(asm_lines):
            result.append("\n")
    return result