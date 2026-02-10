"""Unit tests for the Rust compiler driver."""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from localbolt.compiler.rust_driver import RustCompilerDriver


class TestRustCompilerDriverDiscovery:
    """Test rustc discovery logic."""

    def test_no_rustc_returns_error(self):
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                driver = RustCompilerDriver()
                asm, err = driver.compile("test.rs")
                assert asm == ""
                assert "rustc not found" in err

    def test_discovers_rustc(self):
        with patch("shutil.which", return_value="/usr/bin/rustc"):
            driver = RustCompilerDriver()
            assert driver.compiler == "/usr/bin/rustc"

    def test_discover_compilers_finds_rustc(self):
        with patch("shutil.which", return_value="/usr/bin/rustc"):
            found = RustCompilerDriver.discover_compilers()
            assert "rustc" in found

    def test_discover_compilers_empty_when_missing(self):
        with patch("shutil.which", return_value=None):
            found = RustCompilerDriver.discover_compilers()
            assert found == []


class TestRustCompilerDriverFlags:
    """Test flag translation from generic to Rust-specific."""

    def test_optimization_flag_translation(self):
        with patch("shutil.which", return_value="/usr/bin/rustc"):
            driver = RustCompilerDriver()
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="err", stdout="")
                driver.compile("test.rs", ["-O2"])
                cmd = mock_run.call_args[0][0]
                # Should translate -O2 to -C opt-level=2
                assert "-C" in cmd
                idx = cmd.index("-C")
                # Find the opt-level argument
                opt_args = [a for a in cmd if "opt-level=" in a]
                assert any("opt-level=2" in a for a in opt_args)

    def test_cpp_flags_silently_skipped(self):
        with patch("shutil.which", return_value="/usr/bin/rustc"):
            driver = RustCompilerDriver()
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="err", stdout="")
                driver.compile("test.rs", ["-fverbose-asm", "-masm=intel"])
                cmd = mock_run.call_args[0][0]
                # C++-specific flags should NOT appear
                assert "-fverbose-asm" not in cmd
                assert "-masm=intel" not in cmd

    def test_rust_native_flags_passed_through(self):
        with patch("shutil.which", return_value="/usr/bin/rustc"):
            driver = RustCompilerDriver()
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="err", stdout="")
                driver.compile("test.rs", ["-C", "target-cpu=native"])
                cmd = mock_run.call_args[0][0]
                assert "-C" in cmd

    def test_default_opt_level_when_none_specified(self):
        with patch("shutil.which", return_value="/usr/bin/rustc"):
            driver = RustCompilerDriver()
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="err", stdout="")
                driver.compile("test.rs", [])
                cmd = mock_run.call_args[0][0]
                opt_args = [a for a in cmd if "opt-level=" in a]
                assert any("opt-level=0" in a for a in opt_args)
