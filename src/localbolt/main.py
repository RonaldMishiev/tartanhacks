import sys
import os
import argparse
from .ui.app import run_tui

def run():
    parser = argparse.ArgumentParser(description="LocalBolt: Offline Compiler Explorer")
    parser.add_argument("file", nargs="?", help="C++ source file to watch")
    args = parser.parse_args()

    if not args.file:
        print("Error: No source file specified.")
        print("Usage: localbolt <filename.cpp>")
        sys.exit(1)

    # Resolve to absolute path immediately
    abs_path = os.path.abspath(args.file)

    if not os.path.exists(abs_path):
        print(f"Error: File not found: {abs_path}")
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
