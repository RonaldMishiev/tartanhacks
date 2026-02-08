"""
Tests for Member C — main.py (CLI argument parsing)
=====================================================
Tests the argument parser in isolation — no Textual app is launched.
Matches main branch interface: localbolt <file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from localbolt.main import _build_parser


class TestArgParser:
    """Tests for _build_parser()."""

    def test_basic_file_argument(self):
        """Parser accepts a single positional file argument."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp"])
        assert args.file == "main.cpp"

    def test_no_file_gives_none(self):
        """Without a file arg, args.file should be None (nargs='?')."""
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.file is None

    def test_file_with_path(self):
        """Parser accepts a file with a full path."""
        parser = _build_parser()
        args = parser.parse_args(["/home/user/project/main.cpp"])
        assert args.file == "/home/user/project/main.cpp"

    def test_file_with_relative_path(self):
        """Parser accepts a relative path."""
        parser = _build_parser()
        args = parser.parse_args(["../src/main.cpp"])
        assert args.file == "../src/main.cpp"


class TestRunFunction:
    """Tests for the run() entry point (mocking the app launch)."""

    def test_run_with_no_file_exits(self):
        """run() should sys.exit(1) if no source file is given."""
        from localbolt.main import run

        with patch("sys.argv", ["localbolt"]):
            with pytest.raises(SystemExit) as exc_info:
                run()
            assert exc_info.value.code == 1

    def test_run_calls_run_tui(self):
        """run() should call run_tui with the source file path."""
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as tmp:
            tmp.write(b"int main() {}")
            tmp_path = tmp.name

        mock_run_tui = MagicMock()

        with patch("sys.argv", ["localbolt", tmp_path]):
            with patch("localbolt.main.run_tui", mock_run_tui):
                from localbolt.main import run
                run()

        mock_run_tui.assert_called_once_with(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

    def test_run_catches_keyboard_interrupt(self):
        """run() should not crash on KeyboardInterrupt."""
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as tmp:
            tmp.write(b"int main() {}")
            tmp_path = tmp.name

        with patch("sys.argv", ["localbolt", tmp_path]):
            with patch("localbolt.main.run_tui", side_effect=KeyboardInterrupt):
                from localbolt.main import run
                # Should not raise
                run()

        Path(tmp_path).unlink(missing_ok=True)

    def test_run_catches_generic_exception(self):
        """run() should sys.exit(1) on a generic exception from run_tui."""
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as tmp:
            tmp.write(b"int main() {}")
            tmp_path = tmp.name

        with patch("sys.argv", ["localbolt", tmp_path]):
            with patch("localbolt.main.run_tui", side_effect=RuntimeError("boom")):
                from localbolt.main import run
                with pytest.raises(SystemExit) as exc_info:
                    run()
                assert exc_info.value.code == 1

        Path(tmp_path).unlink(missing_ok=True)
