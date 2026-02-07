from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.style import Style

# Theme Colors (Mosaic)
C_BG = "#EBEEEE"
C_TEXT = "#191A1A"
C_ACCENT1 = "#45d3ee" # Cyan
C_ACCENT2 = "#9FBFC5" # Muted Blue
C_ACCENT3 = "#94bfc1" # Teal
C_ACCENT4 = "#fecd91" # Orange

# Instruction: (Description, Example, Meaning)
ASM_INSTRUCTIONS = {
    "MOV": ("Copies data from one location to another.", "mov eax, ebx", "Copy value from EBX into EAX"),
    "PUSH": ("Pushes a value onto the stack.", "push rax", "Put RAX onto the stack"),
    "POP": ("Pops a value from the stack into a register.", "pop rdi", "Take value from top of stack into RDI"),
    "ADD": ("Adds two operands and stores the result in the first.", "add eax, 5", "EAX = EAX + 5"),
    "SUB": ("Subtracts the second operand from the first.", "sub rsp, 16", "Allocate 16 bytes on the stack"),
    "IMUL": ("Signed multiplication of two operands.", "imul rax, rbx", "RAX = RAX * RBX"),
    "IDIV": ("Signed division.", "idiv rcx", "Divide RDX:RAX by RCX"),
    "INC": ("Increments an operand by 1.", "inc ecx", "ECX = ECX + 1"),
    "DEC": ("Decrements an operand by 1.", "dec edx", "EDX = EDX - 1"),
    "CMP": ("Compares two operands by setting CPU flags.", "cmp eax, 0", "Check if EAX is zero"),
    "JMP": ("Unconditional jump to a label or address.", "jmp .L2", "Always jump to label .L2"),
    "JE/JZ": ("Jump if equal / Jump if zero (ZF=1).", "je .Lerror", "Jump to .Lerror if previous CMP was equal"),
    "JNE/JNZ": ("Jump if not equal / Jump if not zero (ZF=0).", "jne .Lloop", "Jump to .Lloop if previous CMP was not equal"),
    "JG": ("Jump if greater (signed).", "jg .Lgreater", "Jump if left > right (signed)"),
    "JL": ("Jump if less (signed).", "jl .Lless", "Jump if left < right (signed)"),
    "CALL": ("Calls a function; pushes return address to stack.", "call printf", "Execute the printf function"),
    "RET": ("Returns from a function.", "ret", "Return to the calling function"),
    "LEA": ("Load Effective Address (calculates pointer).", "lea rax, [rbp-8]", "Get the address of a local variable"),
    "AND/OR/XOR": ("Bitwise logical operations.", "xor eax, eax", "Quickly set EAX to zero"),
    "NOP": ("No Operation (does nothing for one cycle).", "nop", "Wait/Do nothing for one cycle"),
}

def create_gradient_header(title: str) -> Text:
    text = Text(f" {title} ", style="bold italic")
    # Gradient between Cyan and Blue-Grey
    start_rgb = (69, 211, 238) # #45d3ee
    end_rgb = (159, 191, 197)   # #9FBFC5
    
    for i in range(len(text)):
        ratio = i / len(text)
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        color = f"#{r:02x}{g:02x}{b:02x}"
        text.stylize(color, i, i+1)
    return text

def display_asm_help():
    # Force a light background for the whole console output if possible
    # Note: Rich doesn't easily set global terminal BG, so we wrap in a Panel
    console = Console()
    
    header = create_gradient_header("LOCALBOLT ASSEMBLY REFERENCE")
    
    table = Table(
        title="Popular Assembly Instructions", 
        title_style=f"bold {C_ACCENT3}",
        header_style=f"bold {C_ACCENT1}",
        box=None, # Clean look
        row_styles=["", f"on #f5f7f7"], # Subtle zebra striping on light bg
        expand=True
    )
    
    table.add_column("Instruction", style=f"bold {C_ACCENT1}", no_wrap=True)
    table.add_column("Description", style=C_TEXT)
    table.add_column("Example", style=f"bold {C_ACCENT4}")
    table.add_column("Meaning", style=C_ACCENT3)

    for instr, (desc, example, meaning) in sorted(ASM_INSTRUCTIONS.items()):
        table.add_row(instr, desc, example, meaning)

    # Wrap everything in a Panel with the light background
    main_panel = Panel(
        table,
        title=header,
        title_align="left",
        border_style=C_ACCENT2,
        padding=(1, 2),
        style=f"{C_TEXT} on {C_BG}"
    )

    console.print("\n")
    console.print(main_panel)
    console.print(f"\n[bold {C_TEXT}] Press Q or Ctrl+C to return to terminal.[/bold {C_TEXT}]")
