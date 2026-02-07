try:
    from .parsing.lexer import clean_assembly
    from .parsing.mapper import demangle_stream

    def process_assembly(raw_asm: str) -> str:
        """
        Pipeline: Raw Garbage -> Cleaned -> Demangled -> Human Readable
        """
        cleaned = clean_assembly(raw_asm)
        demangled = demangle_stream(cleaned)
        return demangled
except ImportError:
    # Teammate modules may not be wired up yet; allow partial imports
    pass
