"""
Unit tests for the C++ demangler (mapper.py).
Ensures c++filt integration works and fails gracefully.
"""
import pytest
from unittest.mock import patch, MagicMock
from localbolt.parsing.mapper import demangle_stream


class TestDemangleStream:
    """Test the C++ demangle_stream function."""

    def test_warns_when_cxxfilt_missing(self):
        """Should return assembly with a warning when c++filt is not found."""
        with patch("shutil.which", return_value=None):
            result = demangle_stream("_Z3foov")
            assert "_Z3foov" in result
            assert "WARN" in result

    def test_demangling_with_cxxfilt(self):
        """Should pipe through c++filt and return demangled output."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("foo()\n", "")
        mock_proc.returncode = 0

        with patch("shutil.which", return_value="/usr/bin/c++filt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_stream("_Z3foov")
                assert "foo()" in result

    def test_fallback_on_cxxfilt_error(self):
        """Should return original assembly if c++filt returns non-zero."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "error")
        mock_proc.returncode = 1

        with patch("shutil.which", return_value="/usr/bin/c++filt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_stream("_Z3foov")
                assert result == "_Z3foov"

    def test_fallback_on_exception(self):
        """Should return error message if subprocess throws."""
        with patch("shutil.which", return_value="/usr/bin/c++filt"):
            with patch("subprocess.Popen", side_effect=OSError("boom")):
                result = demangle_stream("_Z3foov")
                assert "Error" in result
                assert "_Z3foov" in result

    def test_empty_input(self):
        """Should handle empty string gracefully."""
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0

        with patch("shutil.which", return_value="/usr/bin/c++filt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_stream("")
                assert isinstance(result, str)

    def test_multiline_input(self):
        """Should handle multi-line assembly correctly."""
        input_asm = "_Z3foov:\n\tpush rbp\n\t_Z3barv\n"
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("foo():\n\tpush rbp\n\tbar()\n", "")
        mock_proc.returncode = 0

        with patch("shutil.which", return_value="/usr/bin/c++filt"):
            with patch("subprocess.Popen", return_value=mock_proc):
                result = demangle_stream(input_asm)
                assert "foo()" in result
                assert "bar()" in result
