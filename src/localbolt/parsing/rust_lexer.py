"""
Rust-specific assembly cleaning patterns.
Supplements the main lexer for Rust-emitted assembly.

These patterns identify Rust internal noise that should be filtered
from the assembly output, just like the C++ lexer filters GCC/Clang noise.
"""
import re

# Rust internal allocator and runtime symbols
RE_RUST_INTERNAL = re.compile(
    r"(__rust_alloc|__rust_dealloc|__rust_realloc|__rust_alloc_zeroed"
    r"|__rust_alloc_error_handler|__rdl_|__rg_)"
)

# Rust panic infrastructure labels
RE_RUST_PANIC = re.compile(
    r"(core::panicking|std::panicking|core::panic|rust_begin_unwind)"
)

# Rust compiler-generated labels (LLVM-style, beyond what the main lexer catches)
RE_RUST_LABELS = re.compile(r"^\s*\.(Ltmp|Lfunc_end|Lfunc_begin|LBB)\d+")

# Rust-specific section names to skip
RE_RUST_SECTIONS = re.compile(
    r"\.(note\.gnu|note\.rustc|rustc|comment|debug_)"
)


def is_rust_noise_line(line: str) -> bool:
    """
    Return True if this assembly line is Rust internal noise
    that should be filtered from output.
    """
    stripped = line.strip()
    if RE_RUST_SECTIONS.search(stripped):
        return True
    if RE_RUST_LABELS.match(stripped):
        return True
    return False


def is_rust_noise_symbol(symbol: str) -> bool:
    """
    Return True if this symbol name is Rust runtime internal.
    Used to filter out labels for internal functions.
    """
    if RE_RUST_INTERNAL.search(symbol):
        return True
    if RE_RUST_PANIC.search(symbol):
        return True
    return False
