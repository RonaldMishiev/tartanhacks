"""
Extended tests for main.py CLI — ensures .rs files are accepted
and unsupported extensions are rejected, without breaking .cpp support.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from localbolt.main import _build_parser, run


class TestArgParserRust:
    """Test that the CLI parser accepts Rust files."""

    def test_rs_file_argument(self):
        parser = _build_parser()
        args = parser.parse_args(["main.rs"])
        assert args.file == "main.rs"

    def test_rs_file_with_path(self):
        parser = _build_parser()
        args = parser.parse_args(["/home/user/project/main.rs"])
        assert args.file == "/home/user/project/main.rs"


class TestRunRustFiles:
    """Test run() behavior with .rs files."""

    def test_run_rs_calls_run_tui(self):
        """run() should call run_tui for a valid .rs file."""
        with tempfile.NamedTemporaryFile(suffix=".rs", delete=False, mode="w") as tmp:
            tmp.write("fn main() {}")
            tmp_path = tmp.name

        mock_run_tui = MagicMock()

        try:
            with patch("sys.argv", ["localbolt", tmp_path]):
                with patch("localbolt.main.run_tui", mock_run_tui):
                    run()
            mock_run_tui.assert_called_once_with(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_run_cpp_still_works(self):
        """Existing .cpp flow must not break."""
        with tempfile.NamedTemporaryFile(suffix=".cpp", delete=False, mode="w") as tmp:
            tmp.write("int main() {}")
            tmp_path = tmp.name

        mock_run_tui = MagicMock()

        try:
            with patch("sys.argv", ["localbolt", tmp_path]):
                with patch("localbolt.main.run_tui", mock_run_tui):
                    run()
            mock_run_tui.assert_called_once_with(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestRunUnsupportedExtensions:
    """Test that unsupported file extensions are rejected."""

    def test_python_file_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as tmp:
            tmp.write("print('hello')")
            tmp_path = tmp.name

        try:
            with patch("sys.argv", ["localbolt", tmp_path]):
                with pytest.raises(SystemExit) as exc_info:
                    run()
                assert exc_info.value.code == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_java_file_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False, mode="w") as tmp:
            tmp.write("class Main {}")
            tmp_path = tmp.name

        try:
            with patch("sys.argv", ["localbolt", tmp_path]):
                with pytest.raises(SystemExit) as exc_info:
                    run()
                assert exc_info.value.code == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_txt_file_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
            tmp.write("hello world")
            tmp_path = tmp.name

        try:
            with patch("sys.argv", ["localbolt", tmp_path]):
                with pytest.raises(SystemExit) as exc_info:
                    run()
                assert exc_info.value.code == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_nonexistent_file_rejected(self):
        with patch("sys.argv", ["localbolt", "/nonexistent/path/main.cpp"]):
            with pytest.raises(SystemExit) as exc_info:
                run()
            assert exc_info.value.code == 1


class TestRunAssemblyHelp:
    """Test --assemblyhelp flag."""

    def test_assemblyhelp_exits_zero(self):
        with patch("sys.argv", ["localbolt", "--assemblyhelp"]):
            with patch("localbolt.main.display_asm_help"):
                with pytest.raises(SystemExit) as exc_info:
                    run()
                assert exc_info.value.code == 0
