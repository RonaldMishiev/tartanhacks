import re
from typing import Dict, List, NamedTuple

class InstructionStats(NamedTuple):
    latency: int
    uops: float
    throughput: float

def parse_mca_output(mca_text: str) -> Dict[int, InstructionStats]:
    """
    Parses the 'Instruction Info' section of llvm-mca output.
    Supports both legacy JSON-like format and standard table format.
    """
    stats_map = {}
    
    in_info_section = False
    header_seen = False
    
    # Format 1: [0]: {1, 0.50, ...}
    regex_legacy = re.compile(r"^\s*\[(\d+)\]:\s*\{(\d+),\s*([\d\.]+),\s*([\d\.]+)")
    
    # Format 2:  1      2     1.00                        add...
    # We just match the first few numbers.
    # Groups: uOps, Latency, RThroughput
    regex_table = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d\.]+)")

    current_idx = 0

    for line in mca_text.splitlines():
        stripped = line.strip()
        
        if "Instruction Info:" in line:
            in_info_section = True
            continue
        
        if in_info_section:
            if not stripped:
                if stats_map: in_info_section = False
                continue
            
            # Check for table header [1] [2] ...
            if "[1]" in line and "[2]" in line:
                header_seen = True
                continue

            # Try Legacy Format
            match = regex_legacy.match(line)
            if match:
                idx = int(match.group(1))
                latency = int(match.group(2))
                uops = float(match.group(3))
                tput = float(match.group(4))
                stats_map[idx] = InstructionStats(latency, uops, tput)
                continue

            # Try Table Format
            if header_seen:
                match = regex_table.match(line)
                if match:
                    uops = int(match.group(1))
                    latency = int(match.group(2))
                    tput = float(match.group(3))
                    
                    stats_map[current_idx] = InstructionStats(latency, float(uops), tput)
                    current_idx += 1

    return stats_map