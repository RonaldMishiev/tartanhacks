import subprocess
import tempfile
import shutil
import platform
from pathlib import Path
from typing import Tuple, List
from .analyzer import find_compile_commands, get_flags_from_db

class CompilerDriver:
    def __init__(self, compiler: str = "g++"):
        # Check if compiler exists
        if not shutil.which(compiler):
            raise RuntimeError(f"Compiler '{compiler}' not found in PATH.")
        self.compiler = compiler

    def compile(self, source_file: str, user_flags: List[str] = []) -> Tuple[str, str]:
        """
        Compiles the source file to assembly.
        Returns: (Assembly String, Error String)
        """
        src_path = Path(source_file)
        
        # 1. Detect Flags from compile_commands.json
        db_path = find_compile_commands(src_path.parent)
        auto_flags = []
        if db_path:
            auto_flags = get_flags_from_db(source_file, db_path)
            
        # 2. Construct the Command
        # -S: Generate assembly
        # -g: Generate debug info (for mapping)
        # -fverbose-asm: Add helpful comments
        # -O3: Default to high optimization (can be overridden)
        command = [
            self.compiler,
            "-S", 
            "-g",
            "-fverbose-asm",
            "-O3" 
        ]

        # Portability: Only use Intel syntax on x86 machines
        arch = platform.machine().lower()
        if any(x in arch for x in ["x86", "amd64", "i386"]):
            command.append("-masm=intel")
        
        # Add discovered flags + user flags
        # Note: User flags come last to override defaults
        command.extend(auto_flags)
        command.extend(user_flags)
        
        # Input file
        command.append(str(src_path))
        
        # Output to a temporary file (so we don't clutter the user's directory)
        with tempfile.NamedTemporaryFile(suffix=".s", mode="w+", delete=False) as tmp:
            output_file = tmp.name
            
        command.extend(["-o", output_file])

        # 3. Run the Compiler
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False # Don't throw exception on compilation error
            )
            
            if result.returncode != 0:
                # Compilation Failed
                return "", result.stderr
            
            # Compilation Succeeded -> Read the temp file
            with open(output_file, 'r') as f:
                asm_content = f.read()
                
            return asm_content, result.stderr # Warnings might still be in stderr

        finally:
            # Cleanup temp file
            if Path(output_file).exists():
                Path(output_file).unlink()

    def analyze_perf(self, asm_content: str) -> str:
        """
        Runs llvm-mca on the generated assembly string.
        """
        if not shutil.which("llvm-mca"):
            return "Error: llvm-mca not installed."
            
        try:
            process = subprocess.Popen(
                ["llvm-mca"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=asm_content)
            
            if process.returncode != 0:
                return f"llvm-mca error: {stderr}"
                
            return stdout
            
        except Exception as e:
            return str(e)
