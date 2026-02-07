import re

# Regex patterns for lines we want to DELETE
# 1. .cfi_ = Call Frame Information (Debugging stack unwinding)
# 2. .LFB / .LFE = Local Function Begin/End (Internal labels)
# 3. .file, .text, .p2align = Section directives
# 4. .size, .type = Metadata
NOISE_PATTERNS = [
    r"^\s*\.cfi_",        
    r"^\s*\.LFB\d+",
    r"^\s*\.LFE\d+",
    r"^\s*\.file",
    r"^\s*\.text",
    r"^\s*\.p2align",
    r"^\s*\.type",
    r"^\s*\.size",
    r"^\s*\.globl",       # Optional: Keep if you want to see exports
    r"^\s*\.section",
    r"^\s*endbr64"        # Intel Control-flow Enforcement (clutter)
]

def clean_assembly(raw_asm: str) -> str:
    """
    Filters out noise lines from the raw assembly string.
    Returns a cleaned string ready for demangling.
    """
    clean_lines = []
    
    for line in raw_asm.splitlines():
        # Skip empty lines
        if not line.strip():
            continue
            
        # Check if line matches any noise pattern
        is_noise = False
        for pattern in NOISE_PATTERNS:
            if re.match(pattern, line):
                is_noise = True
                break
        
        if not is_noise:
            clean_lines.append(line)
            
    return "\n".join(clean_lines)
