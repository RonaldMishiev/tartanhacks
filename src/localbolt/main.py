import sys
import argparse
from .ui.app import run_tui


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(description="LocalBolt: Offline Compiler Explorer")
    parser.add_argument("file", nargs="?", help="C++ source file to watch")
    return parser


def run():
    parser = _build_parser()
    args = parser.parse_args()

    if not args.file:
        print("Error: No source file specified.")
        print("Usage: localbolt <filename.cpp>")
        sys.exit(1)

    try:
        run_tui(args.file)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
