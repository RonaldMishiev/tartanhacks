import re
from dataclasses import dataclass
from typing import List

@dataclass
class Diagnostic:
    line: int
    column: int
    severity: str # 'error' or 'warning'
    message: str

def parse_diagnostics(stderr: str) -> List[Diagnostic]:
    """
    Parses GCC/Clang error output into structured objects.
    Example: hello.cpp:10:5: error: expected ';'
    """
    diagnostics = []
    # Pattern: filename:line:col: severity: message
    pattern = re.compile(r"^.*:(\d+):(\d+):\s+(error|warning):\s+(.*)$", re.MULTILINE)
    
    for match in pattern.finditer(stderr):
        diagnostics.append(Diagnostic(
            line=int(match.group(1)),
            column=int(match.group(2)),
            severity=match.group(3),
            message=match.group(4).strip()
        ))
    
    return diagnostics
