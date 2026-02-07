from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from ..parsing.perf_parser import InstructionStats

@dataclass
class LocalBoltState:
    """
    The single source of truth for the application's data.
    """
    source_path: str = ""
    source_code: str = ""
    
    # Assembly Data
    asm_content: str = ""
    asm_mapping: Dict[int, int] = field(default_factory=dict)
    
    # Performance Data
    perf_stats: Dict[int, InstructionStats] = field(default_factory=dict)
    raw_mca_output: str = ""
    
    # Compiler Metadata
    compiler_output: str = ""
    is_dirty: bool = False  # True if a recompile is needed
    last_update: float = 0.0

    def update_asm(self, asm: str, mapping: Dict[int, int]):
        self.asm_content = asm
        self.asm_mapping = mapping

    def update_perf(self, stats: Dict[int, InstructionStats], raw: str):
        self.perf_stats = stats
        self.raw_mca_output = raw
