import re
import os
from typing import List, Dict, Tuple, Set

# Regex patterns for lines we want to DELETE from the final view
NOISE_PATTERNS = [
    r"^\s*\.cfi_",        
    r"^\s*\.LFB\d+",
    r"^\s*\.LFE\d+",
    r"^\s*\.text",
    r"^\s*\.p2align",
    r"^\s*\.type",
    r"^\s*\.size",
    r"^\s*\.globl",
    r"^\s*\.section",
    r"^\s*endbr64"
]

FILE_PATTERN = r"^\s*\.file\s+(\d+)\s+\"([^\"]+)\""
LOC_PATTERN = r"^\s*\.loc\s+(\d+)\s+(\d+)"

def clean_assembly_with_mapping(raw_asm: str, source_filename: str = None) -> Tuple[str, Dict[int, int]]:
    """
    Filters out noise and assembly from included headers.
    Returns:
        (cleaned_asm_string, {asm_line_idx: source_line_idx})
    """
    clean_lines = []
    line_map = {}
    
    # Map of index -> filename from .file directives
    file_table = {}
    # Indices that belong to our "main" source file
    main_file_indices = set()
    
    current_file_idx = None
    current_source_line = None
    
    # Normalize source filename for comparison
    source_basename = os.path.basename(source_filename) if source_filename else None

    lines = raw_asm.splitlines()
    
    # First pass: Identify which file index corresponds to the user's source file
    for line in lines:
        file_match = re.match(FILE_PATTERN, line)
        if file_match:
            idx, path = int(file_match.group(1)), file_match.group(2)
            file_table[idx] = path
            # If no source_filename provided, assume the first .file is the main one
            if not source_basename or os.path.basename(path) == source_basename:
                main_file_indices.add(idx)

    # Second pass: Filter and map
    for line in lines:
        # Update current file/line context via .loc
        loc_match = re.match(LOC_PATTERN, line)
        if loc_match:
            current_file_idx = int(loc_match.group(1))
            current_source_line = int(loc_match.group(2))
            continue
            
        # Skip noise and directives
        if any(re.match(p, line) for p in NOISE_PATTERNS) or re.match(FILE_PATTERN, line):
            continue
            
        if not line.strip():
            continue

        # Keep labels even if we don't have a .loc context yet, 
        # as they usually precede the first .loc of a function
        is_label = line.strip().endswith(":")
        
        # Only include instructions if they belong to the main source file
        if current_file_idx in main_file_indices or (is_label and current_file_idx is None):
            asm_line_idx = len(clean_lines)
            if current_source_line is not None:
                line_map[asm_line_idx] = current_source_line
            clean_lines.append(line)
            
    return "\n".join(clean_lines), line_map