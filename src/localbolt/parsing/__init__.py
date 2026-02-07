import re
from .lexer import clean_assembly_with_mapping
from .mapper import demangle_stream
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

def process_assembly(raw_asm: str, source_filename: str = None) -> Tuple[str, Dict[int, int]]:
    cleaned, mapping = clean_assembly_with_mapping(raw_asm, source_filename)
    demangled = demangle_stream(cleaned)
    final_asm = simplify_symbols(demangled)
    return final_asm, mapping
