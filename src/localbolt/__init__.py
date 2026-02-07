from .lexer import clean_assembly
from .mapper import demangle_stream

def process_assembly(raw_asm: str) -> str:
    """
    Pipeline: Raw Garbage -> Cleaned -> Demangled -> Human Readable
    """
    cleaned = clean_assembly(raw_asm)
    demangled = demangle_stream(cleaned)
    return demangled
