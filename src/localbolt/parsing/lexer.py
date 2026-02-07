import re
import os
from typing import List, Dict, Tuple, Set, Optional

# --- UNIVERSAL REGEX REGISTRY ---

# 1. NOISE LABELS
# macOS: Lfunc_begin0, l_.str
# Linux: .LBB0_1, .Ltmp0, .LFB0, .LFE0
RE_NOISE_LABEL = re.compile(r"^\s*(\.?)_*[Ll](\d+|BB|func|tmp|return|set|addr|exception|ttbase|cst|ttbaseref|debug|names|info|line|cu|common|str_off|abbrev|FB|FE)[a-zA-Z0-9_$]*:")

# 2. SYSTEM SYMBOLS
# Handles std::, GCC/Clang internals, and ABI hooks
RE_SYSTEM_SYMBOL = re.compile(r"_*Z[NK]*St|GCC_except|___cxa|___gxx|_*clang_call|__stack_chk_fail")

# 3. SECTIONS
# Mach-O (macOS): __TEXT, __cstring
# ELF (Linux): .text, .rodata
RE_SKIP_SECTION = re.compile(r"^\s*\.section\s+.*(__DWARF|__LD|__debug|__apple|__ctf|__llvm|\.debug|\.note|\.comment)", re.IGNORECASE)
RE_CODE_SECTION = re.compile(r"^\s*\.(section\s+.*(__TEXT|text)|text)", re.IGNORECASE)

# 4. DIRECTIVES
RE_DIRECTIVE = re.compile(r"^\s*\.[a-zA-Z0-9_]+")
RE_DATA_DIRECTIVE = re.compile(r"^\s*\.(asciz|string)")

# 5. DWARF / Mapping
RE_FILE = re.compile(r"^\s*\.file\s+(\d+)\s+\"([^\"]+)\"")
RE_LOC = re.compile(r"^\s*\.loc\s+(\d+)\s+(\d+)")

class LexerContext:
    def __init__(self, source_filename: Optional[str]):
        self.main_file_id = 1
        self.source_basename = os.path.basename(source_filename) if source_filename else None
        self.current_source_line = None
        self.active_file_id = None
        self.is_macos = os.uname().sysname.lower() == "darwin"

def clean_assembly_with_mapping(raw_asm: str, source_filename: str = None) -> Tuple[str, Dict[int, int]]:
    ctx = LexerContext(source_filename)
    lines = raw_asm.splitlines()
    
    # 1. Identify File ID
    for line in lines:
        match = RE_FILE.match(line)
        if match:
            fid, path = int(match.group(1)), match.group(2)
            if ctx.source_basename and os.path.basename(path) == ctx.source_basename:
                ctx.main_file_id = fid
                break

    clean_lines = []
    line_map = {}
    in_valid_section = True
    in_user_block = True 
    pending_label = None

    for line in lines:
        line_content = line.split(';')[0].rstrip()
        stripped = line_content.strip()
        if not stripped: continue

        # --- STAGE 1: SECTION FILTER ---
        if stripped.startswith(".section") or stripped in (".text", ".data", ".cstring", ".rodata"):
            if RE_SKIP_SECTION.match(line_content):
                in_valid_section = False
            elif RE_CODE_SECTION.match(line_content):
                in_valid_section = True
            continue

        if not in_valid_section: continue

        # --- STAGE 2: MAPPING ---
        loc_match = RE_LOC.match(line_content)
        if loc_match:
            ctx.active_file_id = int(loc_match.group(1))
            ctx.current_source_line = int(loc_match.group(2))
            continue

        # --- STAGE 3: BLOCK FILTER ---
        is_label = stripped.endswith(":")
        if is_label:
            if RE_SYSTEM_SYMBOL.search(stripped):
                in_user_block = False
                pending_label = None 
                continue
            
            if RE_NOISE_LABEL.match(stripped):
                continue # Procedural noise is never a block start
            
            # User Label
            in_user_block = True
            pending_label = line_content
            continue

        if not in_user_block: continue

        # --- STAGE 4: FILE FILTER ---
        if ctx.active_file_id is not None and ctx.active_file_id != ctx.main_file_id:
            continue

        # --- STAGE 5: INSTRUCTION FILTER ---
        if stripped == "endbr64":
            continue

        if RE_DIRECTIVE.match(line_content) and not is_label:
            if not RE_DATA_DIRECTIVE.match(line_content):
                continue

        # --- STAGE 5: COMMIT & PORTABILITY CLEANUP ---
        if pending_label:
            # Only strip leading underscores on macOS
            if ctx.is_macos:
                pending_label = re.sub(r"\b_([a-zA-Z0-9_$]+)", r"\1", pending_label)
            
            # Remove private label markers (L_ or .L)
            formatted_label = re.sub(r"^\s*(\.?)_*[Ll]_", "", pending_label)
            
            if clean_lines: clean_lines.append("")
            clean_lines.append(formatted_label)
            pending_label = None

        content = line_content
        if ctx.is_macos:
            content = re.sub(r"\b_([a-zA-Z0-9_$]+)", r"\1", content)
        
        asm_line_idx = len(clean_lines)
        if ctx.current_source_line is not None:
            line_map[asm_line_idx] = ctx.current_source_line
        clean_lines.append(content)

    return "\n".join(clean_lines), line_map
