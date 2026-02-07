from rich.console import Console
from rich.table import Table
from rich.panel import Panel

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

def display_asm_help():
    console = Console()
    
    table = Table(title="Popular Assembly Instructions", header_style="bold magenta")
    table.add_column("Instruction", style="cyan", no_wrap=True)
    table.add_column("Description")
    table.add_column("Example", style="green")
    table.add_column("Meaning", style="yellow")

    for instr, (desc, example, meaning) in sorted(ASM_INSTRUCTIONS.items()):
        table.add_row(instr, desc, example, meaning)

    console.print(Panel.fit(
        "LocalBolt Assembly Reference Page", 
        subtitle="Use this to understand the compiled output",
        style="bold blue"
    ))
    console.print(table)
    console.print("\n[bright_black]Press Q or Ctrl+C to return to terminal.[/bright_black]")