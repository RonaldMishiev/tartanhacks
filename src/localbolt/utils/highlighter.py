import re
import shutil
from rich.text import Text

REGISTERS = re.compile(
    r"\b("
    r"r[abcd]x|r[sd]i|r[bs]p|r(?:8|9|1[0-5])[dwb]?"
    r"|e[abcd]x|e[sd]i|e[bs]p"
    r"|[abcd][hl]|[abcd]x|[sd]il?|[bs]pl?"
    r"|xmm[0-9]+|ymm[0-9]+|zmm[0-9]+"
    r"|[wx][0-9]{1,2}|sp|fp|lr" # Added ARM registers
    r")\b",
    re.IGNORECASE,
)

SIZE_KEYWORDS = re.compile(
    r"\b(DWORD|QWORD|WORD|BYTE|PTR)\b",
)

NUMBERS = re.compile(
    r"\b(0x[0-9a-fA-F]+|0b[01]+|[0-9]+)\b",
)

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


def highlight_asm(cleaned_asm: list[str]) -> Text:
    """
    Apply syntax highlighting to cleaned assembly.

    Custom rules applied via Rich Text styling:
      - Registers (rax, rbx, eax, etc.) -> RED / bold
      - Instructions (mov, add, sub, cmp, jmp, call, ret) -> BLUE
      - Comments (lines starting with # or ;) -> bright_black
      - Labels (ending with :) -> YELLOW / bold
      - Size keywords (DWORD, PTR, etc.) -> MAGENTA
      - Numeric literals (42, 0xff, etc.) -> CYAN

    Args:
        cleaned_asm: The noise-free assembly from Member B.

    Returns:
        A Rich Text renderable that Member C can pass to a Static widget.
    """
    asm_str = "\n".join(cleaned_asm) if isinstance(cleaned_asm, list) else cleaned_asm
    text = Text(asm_str)

    for line_match in re.finditer(r"^.*$", asm_str, re.MULTILINE):
        line = line_match.group()
        start = line_match.start()

        # Comments: entire line is bright_black
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith(";"):
            text.stylize("bright_black", start, start + len(line))
            continue
        
        # Labels (e.g. "main:" or ".L1:")
        label_match = re.match(r"^(\s*\.?\w+\s*:)", line)
        if label_match:
            text.stylize("bold yellow", start, start + label_match.end())

        # Instructions
        for m in INSTRUCTIONS.finditer(line):
            text.stylize("blue", start + m.start(), start + m.end())

        # Size keywords (DWORD, PTR, etc.)
        for m in SIZE_KEYWORDS.finditer(line):
            text.stylize("magenta", start + m.start(), start + m.end())

        # Numeric literals
        for m in NUMBERS.finditer(line):
            text.stylize("cyan", start + m.start(), start + m.end())

        # Registers
        for m in REGISTERS.finditer(line):
            text.stylize("bold red", start + m.start(), start + m.end())

    return text


def _severity_styles(cycles: int | None) -> tuple[str, str]:
    """Return (foreground_style, background_color) for a given cycle count."""
    if cycles is None:
        return ("", "")
    if cycles <= 1:
        return ("#ffffff", "on #004400") # Green
    if cycles <= 4:
        return ("#ffffff", "on #664400") # Amber
    return ("#ffffff", "on #880000")    # Red


def _highlight_asm_line(line: str, bg: str) -> Text:
    """
    Syntax-highlight a single assembly line and apply a background tint.

    Tokens are styled with the same asm color scheme layered on top of
    the severity background.
    """
    segment = Text()
    stripped = line.lstrip()

    # Comments: entire line bright_black
    if stripped.startswith("#") or stripped.startswith(";"):
        segment.append(line, style=f"bright_black {bg}".strip())
        return segment

    # Walk through the line applying token-level highlighting
    token_styles: list[str | None] = [None] * len(line)

    # Labels
    label_match = re.match(r"^(\s*\.?\w+\s*:)", line)
    if label_match:
        for j in range(label_match.start(), label_match.end()):
            token_styles[j] = "bold yellow"

    # Instructions
    for m in INSTRUCTIONS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "blue"

    # Size keywords
    for m in SIZE_KEYWORDS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "magenta"

    # Numeric literals
    for m in NUMBERS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "cyan"
    
    # Registers
    for m in REGISTERS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "bold red"

    # Emit characters
    i = 0
    while i < len(line):
        cur_style = token_styles[i]
        j = i
        while j < len(line) and token_styles[j] == cur_style:
            j += 1
        full_style = f"{cur_style} {bg}" if cur_style else bg
        segment.append(line[i:j], style=full_style.strip())
        i = j

    return segment


def build_gutter(asm_lines: list[str], cycle_counts: dict[int, int], width: int = 150) -> Text:
    """
    Builds highlighted ASM where the background color spans the entire line width.
    """
    gutter_width = 6
    result = Text(no_wrap=True)

    for i, line in enumerate(asm_lines):
        line_num = i + 1
        cycles = cycle_counts.get(line_num)
        fg_style, bg = _severity_styles(cycles)

        # 1. Add instructions with background
        line_text = _highlight_asm_line(line, bg)
        result.append_text(line_text)

        # 2. Add padding with background
        padding_needed = max(1, width - len(line) - gutter_width)
        result.append(" " * padding_needed, style=bg.strip() or None)

        # 3. Add cycle count WITH same background
        if cycles is not None:
            result.append(f"{cycles:>{gutter_width}}c", style=f"{fg_style} {bg}".strip())
        else:
            result.append(" " * (gutter_width + 1), style=bg.strip() or None)

        if line_num < len(asm_lines):
            result.append("\n")

    return result