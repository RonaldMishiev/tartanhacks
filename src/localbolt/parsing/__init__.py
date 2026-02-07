from .lexer import clean_assembly_with_mapping
from .mapper import demangle_stream
from .perf_parser import parse_mca_output, InstructionStats
from typing import Dict, Tuple, List, Optional

def process_assembly(raw_asm: str, source_filename: str = None) -> Tuple[str, Dict[int, int]]:

    """

    Complete pipeline: 

    1. Extract .loc mappings and clean noise.

    2. Demangle symbols in the cleaned output.

    Returns (demangled_asm, mapping_dict)

    """

    cleaned, mapping = clean_assembly_with_mapping(raw_asm, source_filename)

    demangled = demangle_stream(cleaned)

    return demangled, mapping
