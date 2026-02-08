import sys
import os
import argparse
from .ui.app import run_tui
from .utils.asm_help import display_asm_help
from .utils.lang import is_supported


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(description="LocalBolt: Offline Compiler Explorer")
    parser.add_argument("file", nargs="?", help="C++ or Rust source file to watch")
    parser.add_argument("--assemblyhelp", action="store_true", help="Display help for popular assembly instructions")
    return parser


def run():
    parser = _build_parser()
    args = parser.parse_args()

    if args.assemblyhelp:
        display_asm_help()
        sys.exit(0)

    if not args.file:
        print("Error: No source file specified.")
        print("Usage: localbolt <filename.cpp|filename.rs>")
        sys.exit(1)

    # Resolve to absolute path immediately
    abs_path = os.path.abspath(args.file)

    if not os.path.exists(abs_path):
        print(f"Error: File not found: {abs_path}")
        sys.exit(1)

    if not is_supported(abs_path):
        print(f"Error: Unsupported file type. Use .cpp, .cc, .c, .cxx, or .rs")
        sys.exit(1)

    try:
        run_tui(abs_path)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
