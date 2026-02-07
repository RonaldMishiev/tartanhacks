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
    # --- Universal / x86 ---
    "MOV": ("Copies data from one location to another.", "mov eax, ebx", "Copy value from EBX into EAX"),
    "PUSH": ("Pushes a value onto the stack (x86).", "push rax", "Put RAX onto the stack"),
    "POP": ("Pops a value from the stack into a register (x86).", "pop rdi", "Take value from top of stack into RDI"),
    "ADD": ("Adds two operands and stores the result in the first.", "add x0, x1, x2", "x0 = x1 + x2"),
    "SUB": ("Subtracts the second operand from the first.", "sub sp, sp, #16", "Allocate 16 bytes on the stack"),
    "IMUL": ("Signed multiplication.", "imul rax, rbx", "RAX = RAX * RBX"),
    "CMP": ("Compares two operands by setting CPU flags.", "cmp w0, #0", "Check if W0 is zero"),
    "RET": ("Returns from a function.", "ret", "Return to the calling function"),
    "LEA": ("Load Effective Address (calculates pointer).", "lea rax, [rbp-8]", "Get the address of a local variable"),
    "CDQ": ("Sign-extends EAX into EDX:EAX. Prepared for 64-bit division.", "cdq", "Sign-extend EAX into EDX"),
    "IDIV": ("Signed divide. Divides EDX:EAX by the operand.", "idiv ecx", "EAX = Quotient, EDX = Remainder"),
    "INC": ("Increments an operand by 1.", "inc eax", "EAX = EAX + 1"),
    "DEC": ("Decrements an operand by 1.", "dec ebx", "EBX = EBX - 1"),
    "JMP": ("Unconditional jump to a label or address.", "jmp .L2", "Always jump to label .L2"),
    "XOR": ("Bitwise exclusive OR. Often used to zero a register.", "xor eax, eax", "Set EAX to 0"),
    "AND": ("Bitwise AND.", "and eax, 7", "Keep only the lower 3 bits of EAX"),
    "OR": ("Bitwise OR.", "or ebx, 1", "Set the lowest bit of EBX to 1"),
    "NOP": ("No Operation. Does nothing for one cycle.", "nop", "Wait/Do nothing"),
    "CALL": ("Calls a function; pushes return address to stack.", "call printf", "Execute the printf function"),
    "TEST": ("Logical compare using AND (sets flags, no result saved).", "test eax, eax", "Check if EAX is zero or negative"),
    "MOVZX": ("Move with Zero-Extend (copies smaller to larger).", "movzx rax, byte ptr [rbp-1]", "Copy byte to 64-bit reg, zero the rest"),
    "SHL/SAL": ("Shift Left: Multiplies by powers of 2.", "shl eax, 1", "EAX = EAX * 2"),
    "SHR": ("Shift Right (logical): Divides by powers of 2.", "shr ebx, 2", "EBX = EBX / 4"),
    "SAR": ("Shift Right (arithmetic): Divides by powers of 2, preserves sign.", "sar eax, 1", "Signed EAX / 2"),
    "LEAVE": ("High-level Procedure Exit (restores EBP and ESP).", "leave", "Clean up stack frame"),
    "SYSCALL": ("System Call: Transitions to kernel mode.", "syscall", "Request OS service"),
    "JE/JZ": ("Jump if Equal / Jump if Zero.", "je .Lerror", "Jump if result was zero"),
    "JNE/JNZ": ("Jump if Not Equal / Jump if Not Zero.", "jne .Lloop", "Jump if result was not zero"),
    "JG": ("Jump if Greater (signed).", "jg .Lbigger", "Jump if left > right"),
    "JL": ("Jump if Less (signed).", "jl .Lsmaller", "Jump if left < right"),
    "JGE": ("Jump if Greater or Equal (signed).", "jge .Ltop", "Jump if left >= right"),
    
    # --- ARM64 Specific (Modern Mac) ---
    "LDR": ("Load Register: Loads a value from memory into a register.", "ldr x0, [x1]", "Load value at address x1 into x0"),
    "STR": ("Store Register: Stores a register value into memory.", "str x0, [sp, #8]", "Store x0 at stack offset 8"),
    "LDP": ("Load Pair: Loads two registers from consecutive memory.", "ldp x29, x30, [sp], #16", "Restore Frame Pointer and Link Reg"),
    "STP": ("Store Pair: Stores two registers into consecutive memory.", "stp x29, x30, [sp, #-16]!", "Save Frame Pointer and Link Reg"),
    "ADRP": ("Address Page: Form PC-relative address to a 4KB page.", "adrp x0, label@PAGE", "Calculate base address of a global"),
    "BL": ("Branch with Link: Calls a function.", "bl _printf", "Execute the printf function"),
    "B": ("Branch: Unconditional jump.", "b .L2", "Always jump to label .L2"),
    "B.": ("Conditional Branch (e.g., B.EQ, B.NE).", "b.eq .Lerror", "Jump if previous comparison was equal"),
    "STUR": ("Store Unscaled: Store register with an unscaled offset.", "stur w0, [x29, #-4]", "Store local variable on stack"),
    "LDUR": ("Load Unscaled: Load register with an unscaled offset.", "ldur w0, [x29, #-4]", "Load local variable from stack"),
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
