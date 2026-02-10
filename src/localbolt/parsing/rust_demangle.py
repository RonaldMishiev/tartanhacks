"""
Rust symbol demangling — uses rustfilt if available, else graceful fallback.
This module is the Rust counterpart of mapper.py's c++filt integration.
"""
import shutil
import subprocess
import re

# Rust appends ::h<16 hex digits> hash suffix to mangled symbol names
RE_RUST_HASH = re.compile(r"::h[0-9a-f]{16}")


def has_rustfilt() -> bool:
    """Check if rustfilt is installed."""
    return shutil.which("rustfilt") is not None


def demangle_rust(text: str) -> str:
    """
    Demangle Rust symbols via rustfilt.
    Falls back to returning text unchanged if rustfilt is not available.
    """
    rustfilt = shutil.which("rustfilt")
    if not rustfilt:
        # Try llvm-cxxfilt as a fallback — recent versions handle Rust mangling
        llvm_filt = shutil.which("llvm-cxxfilt")
        if not llvm_filt:
            return text + "\n# [WARN] rustfilt not found, Rust symbols mangled. Install: cargo install rustfilt"

        try:
            result = subprocess.run(
                [llvm_filt], input=text, capture_output=True, text=True, check=False
            )
            return result.stdout if result.returncode == 0 else text
        except Exception:
            return text

    try:
        process = subprocess.Popen(
            [rustfilt],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=text)
        return stdout if process.returncode == 0 else text

    except Exception as e:
        return f"# Error demangling Rust symbols: {e}\n{text}"


def simplify_rust_symbols(text: str) -> str:
    """
    Strip hash suffixes and verbose stdlib paths from demangled Rust symbols.
    Applied after demangling for readability.
    """
    # Remove ::h<16 hex digits> hash suffixes
    text = RE_RUST_HASH.sub("", text)

    # Shorten common verbose core/alloc paths
    text = text.replace("core::ops::function::FnOnce::", "FnOnce::")
    text = text.replace("core::ops::function::FnMut::", "FnMut::")
    text = text.replace("core::ops::function::Fn::", "Fn::")
    text = text.replace("core::fmt::", "fmt::")
    text = text.replace("alloc::string::String", "String")
    text = text.replace("alloc::vec::Vec", "Vec")

    return text
