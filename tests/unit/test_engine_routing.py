"""
Unit tests for BoltEngine — ensures language-aware routing works
and does NOT break existing C++ behavior.
All compilation is mocked — no real compilers needed.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from localbolt.engine import BoltEngine
from localbolt.utils.lang import Language


def _make_temp_file(suffix: str, content: str = "") -> str:
    """Create a temp file with the given suffix and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w")
    f.write(content)
    f.close()
    return f.name


class TestEngineLanguageRouting:
    """Ensure BoltEngine picks the right driver based on file extension."""

    def test_cpp_file_uses_compiler_driver(self):
        path = _make_temp_file(".cpp", "int main() {}")
        try:
            engine = BoltEngine(path)
            assert engine.language == Language.CPP
            from localbolt.compiler.driver import CompilerDriver
            assert isinstance(engine.driver, CompilerDriver)
        finally:
            os.unlink(path)

    def test_cc_file_uses_compiler_driver(self):
        path = _make_temp_file(".cc", "int main() {}")
        try:
            engine = BoltEngine(path)
            assert engine.language == Language.CPP
        finally:
            os.unlink(path)

    def test_c_file_uses_compiler_driver(self):
        path = _make_temp_file(".c", "int main() {}")
        try:
            engine = BoltEngine(path)
            assert engine.language == Language.CPP
        finally:
            os.unlink(path)

    def test_rs_file_uses_rust_driver(self):
        path = _make_temp_file(".rs", "fn main() {}")
        try:
            engine = BoltEngine(path)
            assert engine.language == Language.RUST
            from localbolt.compiler.rust_driver import RustCompilerDriver
            assert isinstance(engine.driver, RustCompilerDriver)
        finally:
            os.unlink(path)


class TestEngineRefresh:
    """Test engine refresh with mocked compilation."""

    def test_refresh_cpp_calls_process_assembly_with_cpp(self):
        path = _make_temp_file(".cpp", "int main() { return 0; }")
        try:
            engine = BoltEngine(path)
            with patch.object(engine.driver, "compile", return_value=("push rbp\nret", "")):
                with patch.object(engine.driver, "analyze_perf", return_value=""):
                    with patch("localbolt.engine.process_assembly") as mock_pa:
                        mock_pa.return_value = ("clean", {}, "mangled")
                        engine.refresh()
                        # Should be called with language="cpp"
                        mock_pa.assert_called_once()
                        call_kwargs = mock_pa.call_args
                        assert call_kwargs[1].get("language", "cpp") == "cpp" or \
                               (len(call_kwargs[0]) >= 3 and call_kwargs[0][2] == "cpp") or \
                               "language" not in call_kwargs[1]  # default is cpp
        finally:
            os.unlink(path)

    def test_refresh_rust_calls_process_assembly_with_rust(self):
        path = _make_temp_file(".rs", "fn main() {}")
        try:
            engine = BoltEngine(path)
            with patch.object(engine.driver, "compile", return_value=("push rbp\nret", "")):
                with patch.object(engine.driver, "analyze_perf", return_value=""):
                    with patch("localbolt.engine.process_assembly") as mock_pa:
                        mock_pa.return_value = ("clean", {}, "mangled")
                        engine.refresh()
                        mock_pa.assert_called_once()
                        call_args = mock_pa.call_args
                        # Language should be "rust"
                        if call_args[1]:
                            assert call_args[1].get("language") == "rust"
                        else:
                            assert call_args[0][2] == "rust"
        finally:
            os.unlink(path)

    def test_refresh_empty_asm_does_not_crash(self):
        path = _make_temp_file(".cpp", "int main() {}")
        try:
            engine = BoltEngine(path)
            with patch.object(engine.driver, "compile", return_value=("", "error: something")):
                # Should not raise
                engine.refresh()
                assert "error" in engine.state.compiler_output
        finally:
            os.unlink(path)

    def test_refresh_callback_invoked(self):
        path = _make_temp_file(".cpp", "int main() {}")
        try:
            engine = BoltEngine(path)
            callback = MagicMock()
            engine.on_update_callback = callback
            with patch.object(engine.driver, "compile", return_value=("push rbp", "")):
                with patch.object(engine.driver, "analyze_perf", return_value=""):
                    with patch("localbolt.engine.process_assembly", return_value=("c", {}, "m")):
                        engine.refresh()
                        callback.assert_called_once()
        finally:
            os.unlink(path)

    def test_refresh_exception_sets_error_state(self):
        path = _make_temp_file(".cpp", "int main() {}")
        try:
            engine = BoltEngine(path)
            with patch.object(engine.driver, "compile", side_effect=RuntimeError("boom")):
                engine.refresh()
                assert "Internal Engine Error" in engine.state.compiler_output
        finally:
            os.unlink(path)

    def test_set_flags_triggers_refresh(self):
        path = _make_temp_file(".cpp", "int main() {}")
        try:
            engine = BoltEngine(path)
            with patch.object(engine, "refresh") as mock_refresh:
                engine.set_flags(["-O2"])
                assert engine.user_flags == ["-O2"]
                mock_refresh.assert_called_once()
        finally:
            os.unlink(path)
