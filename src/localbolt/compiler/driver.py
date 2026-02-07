import subprocess
import tempfile
import shutil
import platform
from pathlib import Path
from typing import Tuple, List, Optional
from .analyzer import find_compile_commands, get_flags_from_db
from ..utils.config import ConfigManager

class CompilerDriver:
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        # Use provided config or load default
        self.config = config_manager if config_manager else ConfigManager()
        
        # Initialize compiler from config
        target_compiler = self.config.get("compiler", "g++")
        self.set_compiler(target_compiler)

    def set_compiler(self, compiler: str):
        """
        Updates the compiler used by the driver.
        """
        path = shutil.which(compiler)
        if not path:
            # Fallback for common aliases if specifically requested "g++" fails on Mac
            if compiler == "g++" and shutil.which("clang++"):
                path = shutil.which("clang++")
            else:
                # We don't raise here anymore to allow the app to start even if config is stale.
                # The user will get an error when they try to compile.
                print(f"Warning: Compiler '{compiler}' not found.")
                path = None
        
        self.compiler = compiler
        self.compiler_path = path

    @staticmethod
    def discover_compilers() -> List[str]:
        """
        Returns a list of supported compilers found on the system.
        """
        candidates = ["g++", "clang++", "gcc", "clang"]
        found = [c for c in candidates if shutil.which(c)]
        return found

    def compile(self, source_file: str, user_flags: List[str] = []) -> Tuple[str, str]:
        """
        Compiles the source file to assembly.
        Returns: (Assembly String, Error String)
        """
        if not self.compiler_path:
             return "", f"Compiler '{self.compiler}' not configured or not found."

        src_path = Path(source_file)
        
        # --- 1. System Flags (MANDATORY) ---
        # -S: Generate assembly
        # -g: Generate debug info (for mapping)
        # -fverbose-asm: Add helpful comments
        command = [
            self.compiler,
            "-S", 
            "-g",
            "-fverbose-asm"
        ]

        # --- 2. Architecture Flags (SYSTEM ADAPTER) ---
        # Portability: Only use Intel syntax on x86 machines
        arch = platform.machine().lower()
        if any(x in arch for x in ["x86", "amd64", "i386"]):
            command.append("-masm=intel")

        # --- 3. Config Flags (USER PREFERENCE) ---
        # Optimization Level (default to -O3 if missing)
        opt_level = self.config.get("opt_level", "-O3")
        if opt_level:
            command.append(opt_level)
            
        # Extra Config Flags
        extra_conf_flags = self.config.get("flags", [])
        if extra_conf_flags:
            command.extend(extra_conf_flags)

        # --- 4. Auto-Discovery (PROJECT CONTEXT) ---
        db_path = find_compile_commands(src_path.parent)
        auto_flags = []
        if db_path:
            auto_flags = get_flags_from_db(source_file, db_path)
        command.extend(auto_flags)
        
        # --- 5. Runtime Overrides (HIGHEST PRIORITY) ---
        command.extend(user_flags)
        
        # Input/Output
        command.append(str(src_path))
        
        # Output to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".s", mode="w+", delete=False) as tmp:
            output_file = tmp.name
            
        command.extend(["-o", output_file])

        # Run the Compiler
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                return "", result.stderr
            
            with open(output_file, 'r') as f:
                asm_content = f.read()
                
            return asm_content, result.stderr

        finally:
            if Path(output_file).exists():
                Path(output_file).unlink()

    def analyze_perf(self, asm_content: str) -> str:
        """
        Runs llvm-mca on the generated assembly string.
        """
        mca_path = shutil.which("llvm-mca")
        
        # Fallback for macOS Homebrew users where llvm is often not linked
        if not mca_path:
            hb_paths = [
                "/opt/homebrew/opt/llvm/bin/llvm-mca",
                "/usr/local/opt/llvm/bin/llvm-mca"
            ]
            for p in hb_paths:
                if Path(p).exists():
                    mca_path = p
                    break

        if not mca_path:
            return "Error: llvm-mca not installed."
            
        try:
            process = subprocess.Popen(
                [mca_path],
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
