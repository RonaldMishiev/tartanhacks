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


def build_gutter(asm_lines: list[str], cycle_counts: dict[int, int]) -> Text:
    """
    Build a Rich Text object representing the gutter column.

    For each line in asm_lines:
      - If cycle_counts has a value for that line number (1-indexed):
          - Display the number right-aligned in 4 chars
          - Color by severity:
              * 1 cycle  -> green
              * 2-4      -> yellow
              * 5+       -> red / bold red
      - Else: display empty space (4 chars)

    Args:
        asm_lines: The cleaned asm split by lines (from Member B).
        cycle_counts: { asm_line_number: latency } (from Member A's AnalysisResult).

    Returns:
        A Rich Text object with one gutter entry per line, newline-separated.
    """
    gutter = Text()

    gutter_width = 4

    for i, _ in enumerate(asm_lines):
        line_num = i + 1  # 1-indexed
        cycles = cycle_counts.get(line_num)

        if cycles is not None:
            if cycles <= 1:
                style = "green"
            elif cycles <= 4:
                style = "yellow"
            else:
                style = "bold red"
            gutter.append(f"{cycles:<{gutter_width}}", style=style)
        else:
            gutter.append(" " * gutter_width)

        if line_num < len(asm_lines):
            gutter.append("\n")

    return gutter


if __name__ == "__main__":
    from pathlib import Path
    from rich.console import Console

    test_file = Path(__file__).parent / "test_assembly.txt"
    lines = test_file.read_text().splitlines()

    console = Console()
    fake_cycles = {1: 1, 2: 1, 3: 3, 4: 1, 5: 1, 6: 2, 7: 6, 8: 1, 9: 1}
    highlighted = highlight_asm(lines)
    gutter = build_gutter(lines, fake_cycles)
    console.print(highlighted)
    console.print(gutter)

    # # Test build_gutter with fake cycle counts
    # fake_cycles = {1: 1, 2: 1, 3: 3, 4: 1, 5: 1, 6: 2, 7: 6, 8: 1, 9: 1}
    # gutter = build_gutter(lines, fake_cycles)
    # console.print("\n--- Gutter ---")
    # console.print(gutter)
