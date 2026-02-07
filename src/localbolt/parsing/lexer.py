import re
from typing import List, Dict, Tuple

# Regex patterns for lines we want to DELETE from the final view
# We still want to parse .loc before deleting it
NOISE_PATTERNS = [
    r"^\s*\.cfi_",        
    r"^\s*\.LFB\d+",
    r"^\s*\.LFE\d+",
    r"^\s*\.file",
    r"^\s*\.text",
    r"^\s*\.p2align",
    r"^\s*\.type",
    r"^\s*\.size",
    r"^\s*\.globl",
    r"^\s*\.section",
    r"^\s*endbr64"
]

LOC_PATTERN = r"^\s*\.loc\s+\d+\s+(\d+)"

def clean_assembly_with_mapping(raw_asm: str) -> Tuple[str, Dict[int, int]]:
    """
    Filters out noise but extracts .loc directives to map assembly lines back to source lines.
    Returns:
        (cleaned_asm_string, {asm_line_idx: source_line_idx})
    """
    clean_lines = []
    line_map = {}
    current_source_line = None
    
    for line in raw_asm.splitlines():
        # 1. Check for .loc directive
        loc_match = re.match(LOC_PATTERN, line)
        if loc_match:
            current_source_line = int(loc_match.group(1))
            continue # Don't add .loc to output
            
        # 2. Skip empty lines
        if not line.strip():
            continue
            
        # 3. Check if line is other noise
        is_noise = False
        for pattern in NOISE_PATTERNS:
            if re.match(pattern, line):
                is_noise = True
                break
        
        if not is_noise:
            # This is a real instruction or label
            asm_line_idx = len(clean_lines)
            if current_source_line is not None:
                line_map[asm_line_idx] = current_source_line
            clean_lines.append(line)
            
    return "\n".join(clean_lines), line_map