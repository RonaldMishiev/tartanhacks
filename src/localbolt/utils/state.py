from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from ..parsing.perf_parser import InstructionStats
from ..parsing.diagnostics import Diagnostic

@dataclass
class LocalBoltState:
    """
    The single source of truth for the application's data.
    """
    source_path: str = ""
    source_code: str = ""
    source_lines: List[str] = field(default_factory=list)
    
    # Assembly Data
    asm_content: str = ""
    asm_mapping: Dict[int, int] = field(default_factory=dict)
    
    # Performance Data
    perf_stats: Dict[int, InstructionStats] = field(default_factory=dict)
    raw_mca_output: str = ""
    
    # Compiler Metadata & Errors
    compiler_output: str = ""
    user_flags: List[str] = field(default_factory=list)
    diagnostics: List[Diagnostic] = field(default_factory=list)
    last_update: float = 0.0

    @property
    def has_errors(self) -> bool:
        """Returns True if any diagnostic is marked as an error."""
        return any(d.severity == "error" for d in self.diagnostics)

    def get_source_line_for_asm(self, asm_idx: int) -> Optional[str]:
        line_num = self.asm_mapping.get(asm_idx)
        if line_num and 0 < line_num <= len(self.source_lines):
            return self.source_lines[line_num - 1]
        return None

    def update_asm(self, asm: str, mapping: Dict[int, int]):
        self.asm_content = asm
        self.asm_mapping = mapping

    def update_perf(self, stats: Dict[int, InstructionStats], raw: str):
        self.perf_stats = stats
        self.raw_mca_output = raw

    def get_line_number(self, app) -> int:
        """Query the AsmApp for the current cursor line number (1-based)."""
        return app.get_line_number()
