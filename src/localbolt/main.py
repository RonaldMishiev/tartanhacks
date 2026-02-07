"""
LocalBolt — Entry Point
========================
Parses CLI arguments and launches the Textual TUI.

Usage:
    localbolt <source_file.cpp> [-O0|-O1|-O2|-O3] [--flag ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="localbolt",
        description="A local, offline Compiler Explorer in your terminal.",
    )
    parser.add_argument(
        "source",
        help="Path to the C/C++ source file to explore.",
    )
    parser.add_argument(
        "-O",
        "--opt",
        choices=["0", "1", "2", "3", "s", "z"],
        default="0",
        help="Optimization level (default: 0).",
    )
    parser.add_argument(
        "--flag",
        action="append",
        default=[],
        help="Extra compiler flags (can be repeated). E.g. --flag=-march=native",
    )
    return parser


def run() -> None:
    """Console-script entry point (called by `localbolt` command)."""
    parser = _build_parser()
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.is_file():
        print(f"Error: file not found — {source}", file=sys.stderr)
        sys.exit(1)

    flags: list[str] = [f"-O{args.opt}"] + args.flag

    from localbolt.ui.app import LocalBoltApp

    app = LocalBoltApp(source_file=str(source), flags=flags)
    app.run()


if __name__ == "__main__":
    run()
