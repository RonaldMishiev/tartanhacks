import json
import os
import shlex
from pathlib import Path
from typing import List, Optional

def find_compile_commands(root_dir: str = ".") -> Optional[Path]:
    """
    Searches for compile_commands.json in standard build locations.
    """
    # Common places where CMake puts this file
    search_paths = [
        Path(root_dir) / "compile_commands.json",
        Path(root_dir) / "build" / "compile_commands.json",
        Path(root_dir) / "out" / "compile_commands.json",
        Path(root_dir) / "debug" / "compile_commands.json",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    return None

def get_flags_from_db(source_file: str, db_path: Path) -> List[str]:
    """
    Parses the JSON database to find flags for a specific file.
    """
    try:
        with open(db_path, 'r') as f:
            commands = json.load(f)
            
        # Normalize paths for comparison
        abs_source = str(Path(source_file).resolve())
        
        for entry in commands:
            # Entry usually looks like: {"directory": "...", "command": "g++ -I... -c file.cpp", "file": "..."}
            entry_file = str(Path(entry.get('directory', '.'), entry['file']).resolve())
            
            if entry_file == abs_source:
                # We found the file! Now extract flags.
                # The 'command' string includes the compiler (g++) and the file itself.
                # We need to strip those and keep only the -I, -D, -std flags.
                args = shlex.split(entry['command'])
                
                # Filter useful flags (Include paths, Defines, Standards)
                # Skip the compiler binary (index 0) and the input file
                useful_flags = []
                for arg in args[1:]:
                    if arg.startswith(("-I", "-D", "-std", "-f", "-m")):
                        useful_flags.append(arg)
                return useful_flags
                
    except Exception as e:
        print(f"Error parsing compile commands: {e}")
        
    return [] # Fallback: No flags found