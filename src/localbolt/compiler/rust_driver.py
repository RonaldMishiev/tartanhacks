"""
Rust compilation driver — parallel to the C++ CompilerDriver.
Handles rustc compilation and assembly emission without touching
any existing C++ compilation logic.
"""
import re
import subprocess
import shutil
import platform
import tempfile
from pathlib import Path
from typing import Tuple, List, Optional

# Patterns for lines that should be stripped before sending to llvm-mca.
# llvm-mca only understands instructions — labels, directives, and data confuse it.
_RE_MCA_NOISE = re.compile(
    r"^\s*(\."                          # any directive (.asciz, .section, .globl, etc.)
    r"|[a-zA-Z_][\w$.]*:)"             # or any label (foo:, LBB0_1:, _ZN...:)
)
_RE_EMPTY_OR_COMMENT = re.compile(r"^\s*(;.*)?$")


class RustCompilerDriver:
    """Handles rustc compilation and assembly emission."""

    def __init__(self):
        self.compiler: Optional[str] = self._discover_compiler()
        self.compiler_path: Optional[str] = self.compiler  # for interface compat with CompilerDriver

    @staticmethod
    def _discover_compiler() -> Optional[str]:
        """Find rustc on the system."""
        path = shutil.which("rustc")
        if path:
            return path
        # Common rustup install locations
        home = Path.home()
        candidates = [
            home / ".cargo" / "bin" / "rustc",
            home / ".rustup" / "toolchains" / "stable-x86_64-apple-darwin" / "bin" / "rustc",
            home / ".rustup" / "toolchains" / "stable-aarch64-apple-darwin" / "bin" / "rustc",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    @staticmethod
    def discover_compilers() -> List[str]:
        """Returns a list of Rust compilers found on the system."""
        found = []
        if shutil.which("rustc"):
            found.append("rustc")
        return found

    def set_compiler(self, compiler: str):
        """Update the compiler path (interface compat with CompilerDriver)."""
        path = shutil.which(compiler)
        if path:
            self.compiler = compiler
            self.compiler_path = path
        else:
            print(f"Warning: Rust compiler '{compiler}' not found.")

    def compile(self, source_file: str, user_flags: List[str] = []) -> Tuple[str, str]:
        """
        Compile a .rs file to assembly.
        Returns: (Assembly String, Error String)
        """
        if not self.compiler:
            return "", "Error: rustc not found. Install via https://rustup.rs/"

        with tempfile.NamedTemporaryFile(suffix=".s", delete=False) as tmp:
            output_file = tmp.name

        # Base command: emit assembly with debug info for source mapping
        command = [
            self.compiler,
            "--emit", "asm",
            "-C", "debuginfo=2",
        ]

        # Architecture: request Intel syntax on x86 for consistency with C++ output
        arch = platform.machine().lower()
        if any(x in arch for x in ["x86", "x86_64", "amd64", "i386"]):
            command.extend(["-C", "llvm-args=--x86-asm-syntax=intel"])

        # Map user flags — translate common C++ flag forms to Rust equivalents
        has_opt = False
        for flag in user_flags:
            if flag in ("-O0", "-O1", "-O2", "-O3"):
                level = flag[-1]
                command.extend(["-C", f"opt-level={level}"])
                has_opt = True
            elif flag.startswith("-C") or flag.startswith("--"):
                # Pass Rust-native flags through directly
                command.append(flag)
            # Silently skip C++-specific flags like -masm=intel, -fverbose-asm, etc.

        # Default to no optimization if none specified
        if not has_opt:
            command.extend(["-C", "opt-level=0"])

        command.extend(["-o", output_file])
        command.append(str(Path(source_file).resolve()))

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                return "", result.stderr

            with open(output_file, "r") as f:
                asm_content = f.read()
            return asm_content, result.stderr

        except Exception as e:
            return "", f"Rust compilation error: {e}"

        finally:
            if Path(output_file).exists():
                Path(output_file).unlink()

    def analyze_perf(self, asm_content: str) -> str:
        """
        Runs llvm-mca on the generated assembly.
        Rust assembly needs sanitization: strip labels, directives, and data
        that llvm-mca cannot process (it only understands instructions).
        """
        # Sanitize: keep only instruction lines for llvm-mca
        sanitized_lines = []
        for line in asm_content.splitlines():
            if _RE_EMPTY_OR_COMMENT.match(line):
                continue
            if _RE_MCA_NOISE.match(line):
                continue
            sanitized_lines.append(line)

        if not sanitized_lines:
            return "Error: no assembly instructions found after sanitization."

        sanitized = "\n".join(sanitized_lines)

        mca_path = shutil.which("llvm-mca")

        # Fallback for macOS Homebrew users
        if not mca_path:
            hb_paths = [
                "/opt/homebrew/opt/llvm/bin/llvm-mca",
                "/usr/local/opt/llvm/bin/llvm-mca",
            ]
            for p in hb_paths:
                if Path(p).exists():
                    mca_path = p
                    break

        if not mca_path:
            return "Error: llvm-mca not installed."

        try:
            process = subprocess.Popen(
                [mca_path, "--skip-unsupported-instructions=parse-failure"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=sanitized)

            if process.returncode != 0:
                return f"llvm-mca error: {stderr}"

            return stdout

        except Exception as e:
            return str(e)
