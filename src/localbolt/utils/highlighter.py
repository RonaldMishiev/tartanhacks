import re
import shutil

from rich.text import Text

REGISTERS = re.compile(
    r"\b("
    r"r[abcd]x|r[sd]i|r[bs]p|r(?:8|9|1[0-5])[dwb]?"
    r"|e[abcd]x|e[sd]i|e[bs]p"
    r"|[abcd][hl]|[abcd]x|[sd]il?|[bs]pl?"
    r"|xmm[0-9]+|ymm[0-9]+|zmm[0-9]+"
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
    r"|cmov\w+"
    r")\b",
    re.IGNORECASE,
)


def highlight_asm(cleaned_asm: list[str]) -> Text:
    """
    Apply syntax highlighting to cleaned assembly.

    Custom rules applied via Rich Text styling:
      - Registers (rax, rbx, eax, etc.) -> RED / bold
      - Instructions (mov, add, sub, cmp, jmp, call, ret) -> BLUE
      - Comments (lines starting with # or ;) -> DIM / GREY
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

        # Comments: entire line is dim grey
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith(";"):
            text.stylize("dim grey", start, start + len(line))
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
        return ("#005500", "on #103010")
    if cycles <= 4:
        return ("#806600", "on #302510")
    return ("#882222", "on #301010")


def _highlight_asm_line(line: str, bg: str) -> Text:
    """
    Syntax-highlight a single assembly line and apply a background tint.

    Tokens are styled with the same asm color scheme (instructions blue,
    registers bold red, etc.) layered on top of the severity background.
    """
    segment = Text()
    stripped = line.lstrip()

    # Comments: entire line dim grey
    if stripped.startswith("#") or stripped.startswith(";"):
        segment.append(line, style=f"dim grey {bg}")
        return segment

    # Walk through the line applying token-level highlighting
    # Build a style map: for each character position, track the best style
    token_styles: list[str | None] = [None] * len(line)

    # Labels (e.g. "main:" or ".L1:")
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
    
    # Registers (highest priority among tokens)
    for m in REGISTERS.finditer(line):
        for j in range(m.start(), m.end()):
            token_styles[j] = "bold red"

    # Emit characters, grouping consecutive runs of the same style
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


def build_gutter(asm_lines: list[str], cycle_counts: dict[int, int]) -> Text:
    """
    Build a Rich Text object with syntax-highlighted assembly on the left,
    cycle counts right-aligned to the terminal edge, and a severity-tinted
    background spanning each full line.

    Background tints by severity:
        * 1 cycle  -> subtle green  (#002200)
        * 2-4      -> subtle amber  (#332200)
        * 5+       -> subtle red    (#330000)
        * no data  -> no background

    Args:
        asm_lines: The cleaned asm split by lines (from Member B).
        cycle_counts: { asm_line_number: latency } (from Member A's AnalysisResult).

    Returns:
        A Rich Text object with highlighted asm + right-aligned gutter per line.
    """
    term_width = shutil.get_terminal_size().columns
    gutter_width = 6
    result = Text()

    for i, line in enumerate(asm_lines):
        line_num = i + 1
        cycles = cycle_counts.get(line_num)
        fg_style, bg = _severity_styles(cycles)

        # Syntax-highlighted asm text with severity background
        result.append_text(_highlight_asm_line(line, bg))

        # Padding between asm and gutter (same background)
        padding_needed = max(1, term_width - len(line) - gutter_width)
        result.append(" " * padding_needed, style=bg.strip() or None)

        # Cycle count on the right
        if cycles is not None:
            result.append(f"{cycles:>{gutter_width}}", style=f"{fg_style} {bg}".strip())
        else:
            result.append(" " * gutter_width)

        if line_num < len(asm_lines):
            result.append("\n")

    return result


if __name__ == "__main__":
    from pathlib import Path
    from rich.console import Console

    test_file = Path(__file__).parent / "test_assembly.txt"
    lines = test_file.read_text().splitlines()

    console = Console()
    fake_cycles = {1: 1, 2: 1, 3: 3, 4: 1, 5: 1, 6: 2, 7: 6, 8: 1, 9: 1}
    combined = build_gutter(lines, fake_cycles)
    console.print(combined)
