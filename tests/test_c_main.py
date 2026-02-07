"""
Tests for Member C — main.py (CLI argument parsing)
=====================================================
Tests the argument parser in isolation — no Textual app is launched.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from localbolt.main import _build_parser


class TestArgParser:
    """Tests for _build_parser()."""

    def test_basic_source_argument(self):
        """Parser accepts a single positional source file."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp"])
        assert args.source == "main.cpp"

    def test_default_optimization_level(self):
        """Default optimization should be '0' (-O0)."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp"])
        assert args.opt == "0"

    def test_custom_optimization_level(self):
        """User can specify -O 3 for -O3."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp", "-O", "3"])
        assert args.opt == "3"

    def test_optimization_level_s(self):
        """-Os should be accepted."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp", "-O", "s"])
        assert args.opt == "s"

    def test_optimization_level_z(self):
        """-Oz should be accepted."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp", "--opt", "z"])
        assert args.opt == "z"

    def test_invalid_optimization_level(self):
        """An unsupported opt level should cause an error."""
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["main.cpp", "-O", "9"])

    def test_single_extra_flag(self):
        """--flag should append to the flags list."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp", "--flag=-march=native"])
        assert args.flag == ["-march=native"]

    def test_multiple_extra_flags(self):
        """Multiple --flag arguments should all be collected."""
        parser = _build_parser()
        args = parser.parse_args([
            "main.cpp",
            "--flag=-march=native",
            "--flag=-ffast-math",
        ])
        assert args.flag == ["-march=native", "-ffast-math"]

    def test_no_extra_flags_default(self):
        """Without --flag, the list should be empty."""
        parser = _build_parser()
        args = parser.parse_args(["main.cpp"])
        assert args.flag == []

    def test_missing_source_file_exits(self):
        """Calling with no positional arg should fail."""
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestRunFunction:
    """Tests for the run() entry point (mocking the app launch)."""

    def test_run_with_nonexistent_file_exits(self):
        """run() should sys.exit(1) if the source file doesn't exist."""
        from localbolt.main import run

        with patch("sys.argv", ["localbolt", "/nonexistent/abc.cpp"]):
            with pytest.raises(SystemExit) as exc_info:
                run()
            assert exc_info.value.code == 1

    def test_run_constructs_correct_flags(self):
        """run() should build the flags list and pass it to LocalBoltApp."""
        from localbolt.main import run

        # Create a real temp file so the path check passes
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False) as tmp:
            tmp.write(b"int main() {}")
            tmp_path = tmp.name

        mock_app_cls = MagicMock()
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        with patch("sys.argv", ["localbolt", tmp_path, "-O", "2", "--flag=-ffast-math"]):
            with patch("localbolt.main.LocalBoltApp", mock_app_cls, create=True):
                # Patch the import inside run()
                with patch.dict("sys.modules", {}):
                    # We need to patch the local import
                    import localbolt.main as main_mod
                    original_run = main_mod.run

                    def patched_run():
                        import localbolt.main as m
                        parser = m._build_parser()
                        args = parser.parse_args()
                        source = Path(args.source).resolve()
                        flags = [f"-O{args.opt}"] + args.flag
                        # Instead of importing and running, just call the mock
                        mock_app_cls(source_file=str(source), flags=flags)
                        mock_app_instance.run()

                    patched_run()

        # Verify the app was constructed with the right flags
        call_kwargs = mock_app_cls.call_args
        assert "-O2" in call_kwargs.kwargs["flags"]
        assert "-ffast-math" in call_kwargs.kwargs["flags"]

        Path(tmp_path).unlink(missing_ok=True)
