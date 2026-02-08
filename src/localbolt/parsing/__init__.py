import re
from .lexer import clean_assembly_with_mapping
from .mapper import demangle_stream
from .rust_demangle import demangle_rust, simplify_rust_symbols
from .perf_parser import parse_mca_output, InstructionStats
from .diagnostics import parse_diagnostics, Diagnostic
from typing import Dict, Tuple, List, Optional

# --- AESTHETIC CLEANUP PATTERNS ---
RE_STL_VERSIONING = re.compile(r"std::__[1-9]::")
RE_ABI_TAGS = re.compile(r"\[abi:[a-zA-Z0-9]+\]")

def simplify_symbols(text: str) -> str:
    text = RE_STL_VERSIONING.sub("std::", text)
    text = RE_ABI_TAGS.sub("", text)
    return text

def process_assembly(raw_asm: str, source_filename: str = None, language: str = "cpp") -> Tuple[str, Dict[int, int], str]:
    """
    Returns: (demangled_asm, mapping, mangled_cleaned_asm)
    The language parameter defaults to "cpp" so all existing callers are unaffected.
    """
    cleaned_mangled, mapping = clean_assembly_with_mapping(raw_asm, source_filename)

    if language == "rust":
        demangled = demangle_rust(cleaned_mangled)
        final_asm = simplify_rust_symbols(demangled)
    else:
        demangled = demangle_stream(cleaned_mangled)
        final_asm = simplify_symbols(demangled)

    return final_asm, mapping, cleaned_mangled