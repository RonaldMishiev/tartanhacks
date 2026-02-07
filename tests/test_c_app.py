"""
Tests for Member C — app.py
=============================
Tests the LocalBoltApp UI wiring logic with MOCKED engine/teammates.

The engine (BoltEngine) is completely mocked — these tests verify
that Member C's UI layer works correctly in isolation:
  - Widget tree composition (#asm-view, #error-view, Header, Footer)
  - State update message handling (assembly + error modes)
  - action_refresh wiring
  - Error handling

All teammate modules are faked so these tests run standalone.
"""

from __future__ import annotations

import importlib
import sys
import tempfile
import types
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.text import Text
from textual.widgets import Static, TextArea


# ────────────────────────────────────────────────────────────
# Fake state/engine matching main branch interfaces
# ────────────────────────────────────────────────────────────
@dataclass
class FakeInstructionStats:
    latency: int = 1
    uops: float = 0.5
    throughput: float = 0.5


@dataclass
class FakeDiagnostic:
    severity: str = "error"
    message: str = "test"
    line: int = 1
    column: int = 1


@dataclass
class FakeState:
    source_path: str = ""
    source_code: str = ""
    source_lines: list = field(default_factory=list)
    asm_content: str = "push rbp\nmov rbp, rsp\nret"
    asm_mapping: dict = field(default_factory=dict)
    perf_stats: dict = field(default_factory=dict)
    raw_mca_output: str = ""
    compiler_output: str = ""
    diagnostics: list = field(default_factory=list)
    last_update: float = 0.0

    @property
    def has_errors(self) -> bool:
        return any(getattr(d, "severity", "") == "error" for d in self.diagnostics)

    def get_source_line_for_asm(self, asm_idx):
        return None

    def update_asm(self, asm, mapping):
        self.asm_content = asm
        self.asm_mapping = mapping

    def update_perf(self, stats, raw):
        self.perf_stats = stats
        self.raw_mca_output = raw


class FakeEngine:
    """Mimics BoltEngine from main's engine.py."""

    def __init__(self, source_file: str):
        self.state = FakeState(source_path=source_file)
        self.on_update_callback = None
        self._started = False
        self._refreshed = False
        self._stopped = False

    def start(self):
        self._started = True
        if self.on_update_callback:
            self.on_update_callback(self.state)

    def stop(self):
        self._stopped = True

    def refresh(self):
        self._refreshed = True
        if self.on_update_callback:
            self.on_update_callback(self.state)


class FakeFileWatcher:
    def start_watching(self, *a, **k):
        pass
    def stop_watching(self, *a, **k):
        pass


def _fake_build_gutter(asm_lines, cycle_counts, width=150):
    """Return a real Rich Text object so Static.update() doesn't crash."""
    return Text("\n".join(asm_lines)) if asm_lines else Text("")


# ────────────────────────────────────────────────────────────
# Inject fake teammate modules into sys.modules
# ────────────────────────────────────────────────────────────
def _inject_fakes(engine_instance=None):
    """
    Inject fake versions of all teammate modules so app.py can import.
    Returns (fakes_dict, cleanup_function).
    """
    originals = {}

    # --- localbolt.parsing.perf_parser ---
    pp_mod = types.ModuleType("localbolt.parsing.perf_parser")
    pp_mod.InstructionStats = FakeInstructionStats
    pp_mod.parse_mca_output = MagicMock(return_value={})

    # --- localbolt.parsing.diagnostics ---
    diag_mod = types.ModuleType("localbolt.parsing.diagnostics")
    diag_mod.Diagnostic = FakeDiagnostic
    diag_mod.parse_diagnostics = MagicMock(return_value=[])

    # --- localbolt.parsing (parent) ---
    parsing_mod = types.ModuleType("localbolt.parsing")
    parsing_mod.process_assembly = MagicMock(return_value=("push rbp\nret", {}))
    parsing_mod.parse_mca_output = MagicMock(return_value={})
    parsing_mod.parse_diagnostics = MagicMock(return_value=[])

    # --- localbolt.utils.state ---
    state_mod = types.ModuleType("localbolt.utils.state")
    state_mod.LocalBoltState = FakeState

    # --- localbolt.utils.watcher ---
    watcher_mod = types.ModuleType("localbolt.utils.watcher")
    watcher_mod.FileWatcher = FakeFileWatcher

    # --- localbolt.utils.highlighter ---
    # build_gutter MUST return a valid Rich renderable (Text), not None!
    hl_mod = types.ModuleType("localbolt.utils.highlighter")
    hl_mod.highlight_asm = MagicMock(side_effect=lambda lines: Text("\n".join(lines) if isinstance(lines, list) else lines))
    hl_mod.build_gutter = MagicMock(side_effect=_fake_build_gutter)
    # highlight_asm_line and severity_styles needed by the new per-line app.py
    hl_mod.highlight_asm_line = MagicMock(side_effect=lambda line, bg: Text(line))
    hl_mod.severity_styles = MagicMock(side_effect=lambda cycles: ("", "") if cycles is None else ("#fff", "on #004400"))
    # INSTRUCTIONS regex needed by app.py for alignment logic
    import re
    hl_mod.INSTRUCTIONS = re.compile(
        r"\b(movs?[xzbw]?|lea|add|sub|imul|idiv|mul|div|inc|dec"
        r"|cmp|test|and|or|xor|not|shl|shr|sar|sal"
        r"|jmp|je|jne|jz|jnz|jg|jge|jl|jle|ja|jae|jb|jbe"
        r"|call|ret|push|pop|nop|int|syscall|leave|enter"
        r"|cmov\w+|stp|ldp|stur|ldur|adrp|bl|b\.)\b",
        re.IGNORECASE,
    )

    # --- localbolt.compiler.driver ---
    driver_mod = types.ModuleType("localbolt.compiler.driver")
    driver_mod.CompilerDriver = MagicMock

    # --- localbolt.engine ---
    engine_mod = types.ModuleType("localbolt.engine")
    if engine_instance is not None:
        engine_mod.BoltEngine = lambda source_file: engine_instance
    else:
        engine_mod.BoltEngine = FakeEngine

    # --- localbolt.utils.asm_help ---
    asm_help_mod = types.ModuleType("localbolt.utils.asm_help")
    asm_help_mod.ASM_INSTRUCTIONS = {}

    # --- localbolt.ui.instruction_help ---
    # We let instruction_help import naturally since it only needs asm_help
    # and highlighter which we already faked, but we must pop it for reimport
    instr_help_mod = None  # will be reimported naturally

    fakes = {
        "localbolt.parsing.perf_parser": pp_mod,
        "localbolt.parsing.diagnostics": diag_mod,
        "localbolt.parsing": parsing_mod,
        "localbolt.utils.state": state_mod,
        "localbolt.utils.watcher": watcher_mod,
        "localbolt.utils.highlighter": hl_mod,
        "localbolt.utils.asm_help": asm_help_mod,
        "localbolt.compiler.driver": driver_mod,
        "localbolt.engine": engine_mod,
    }

    for name, mod in fakes.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod

    # Force reimport of app.py so it picks up the fakes
    sys.modules.pop("localbolt.ui.app", None)
    sys.modules.pop("localbolt.ui.source_peek", None)
    sys.modules.pop("localbolt.ui.instruction_help", None)

    def cleanup():
        sys.modules.pop("localbolt.ui.app", None)
        sys.modules.pop("localbolt.ui.source_peek", None)
        sys.modules.pop("localbolt.ui.instruction_help", None)
        for name in fakes:
            if originals[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = originals[name]

    return fakes, cleanup


# ────────────────────────────────────────────────────────────
# Helper: create a temp .cpp file
# ────────────────────────────────────────────────────────────
def _make_tmp_cpp(content: str = "int main() { return 0; }\n") -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False)
    f.write(content)
    f.flush()
    f.close()
    return f.name


# ────────────────────────────────────────────────────────────
# App composition tests — matches actual app.py widget IDs
# ────────────────────────────────────────────────────────────
class TestAppComposition:
    """Verify the widget tree is assembled correctly."""

    @pytest.mark.asyncio
    async def test_app_has_asm_lines(self):
        """App should populate AsmLine widgets after engine state update."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.asm_content = "push rbp\nmov rbp, rsp\nret"
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp, AsmLine
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                lines = pilot.app.query(AsmLine)
                assert len(lines) == 3
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_app_has_error_view(self):
        """App should have a TextArea with id='error-view'."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                ev = pilot.app.query_one("#error-view", TextArea)
                assert ev is not None
                assert ev.read_only is True
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_app_has_no_source_view(self):
        """SourceView should NOT be in the widget tree (assembly-only UI)."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                results = pilot.app.query("#source-view")
                assert len(results) == 0
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_app_has_footer(self):
        """App should have a Footer widget."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                from textual.widgets import Footer
                assert pilot.app.query_one(Footer) is not None
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)


# ────────────────────────────────────────────────────────────
# App init tests
# ────────────────────────────────────────────────────────────
class TestAppInit:
    """Verify constructor stores values correctly."""

    def test_engine_is_created(self):
        """App should create a BoltEngine in __init__."""
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file="/tmp/test.cpp")
            assert app.engine is not None
        finally:
            cleanup()

    def test_engine_callback_is_set(self):
        """App should set the on_update_callback on the engine."""
        engine = FakeEngine("/tmp/test.cpp")
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file="/tmp/test.cpp")
            assert app.engine.on_update_callback is not None
        finally:
            cleanup()


# ────────────────────────────────────────────────────────────
# Engine integration tests (mocked engine)
# ────────────────────────────────────────────────────────────
class TestEngineIntegration:
    """Test that the app correctly wires up to BoltEngine."""

    @pytest.mark.asyncio
    async def test_engine_is_started_on_mount(self):
        """The engine should be started when the app mounts."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                assert engine._started
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_asm_lines_populated_on_state_update(self):
        """After engine state update with asm, AsmLine widgets should be created."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.asm_content = "push rbp\nmov rbp, rsp\npop rbp\nret"
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp, AsmLine
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                lines = pilot.app.query(AsmLine)
                assert len(lines) == 4
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_action_refresh_calls_engine(self):
        """Pressing 'r' should call engine.refresh()."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                engine._refreshed = False  # reset after initial start() call
                await pilot.press("r")
                await pilot.pause()
                assert engine._refreshed
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_error_mode_on_diagnostics(self):
        """When state has errors, error-view should be visible."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.diagnostics = [FakeDiagnostic(severity="error", message="boom")]
        engine.state.compiler_output = "fatal error: file not found"
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                error_view = pilot.app.query_one("#error-view", TextArea)
                assert error_view.display is True
                assert "fatal error" in error_view.text
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_assembly_mode_when_no_errors(self):
        """When state has no errors, AsmLine widgets should be visible, error-view hidden."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.asm_content = "push rbp\nret"
        engine.state.diagnostics = []
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp, AsmLine
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                error_view = pilot.app.query_one("#error-view", TextArea)
                asm_lines = pilot.app.query(AsmLine)
                assert len(asm_lines) == 2
                assert error_view.display is False
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_engine_failure_raises(self):
        """If BoltEngine constructor raises, LocalBoltApp should propagate it."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()

        engine_mod = types.ModuleType("localbolt.engine")
        def bad_engine(source_file):
            raise RuntimeError("Engine not available")
        engine_mod.BoltEngine = bad_engine
        sys.modules["localbolt.engine"] = engine_mod
        sys.modules.pop("localbolt.ui.app", None)
        sys.modules.pop("localbolt.ui.instruction_help", None)

        try:
            from localbolt.ui.app import LocalBoltApp
            with pytest.raises(RuntimeError, match="Engine not available"):
                app = LocalBoltApp(source_file=tmp)
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_cursor_navigation(self):
        """Pressing j/k or up/down should move the cursor between AsmLine widgets."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.asm_content = "push rbp\nmov rbp, rsp\npop rbp\nret"
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp, AsmLine
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                assert app._cursor == 0
                # Move down
                await pilot.press("j")
                await pilot.pause()
                assert app._cursor == 1
                # Move down again
                await pilot.press("down")
                await pilot.pause()
                assert app._cursor == 2
                # Move up
                await pilot.press("k")
                await pilot.pause()
                assert app._cursor == 1
                # Move up with arrow
                await pilot.press("up")
                await pilot.pause()
                assert app._cursor == 0
                # Can't go above 0
                await pilot.press("up")
                await pilot.pause()
                assert app._cursor == 0
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)


# ────────────────────────────────────────────────────────────
# Source Peek tests
# ────────────────────────────────────────────────────────────
class TestSourcePeek:
    """Test the source peek panel integration."""

    @pytest.mark.asyncio
    async def test_app_has_source_peek(self):
        """App should have a SourcePeekPanel with id='source-peek'."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            from localbolt.ui.source_peek import SourcePeekPanel
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                sp = pilot.app.query_one("#source-peek", SourcePeekPanel)
                assert sp is not None
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_source_peek_updates_with_mapping(self):
        """After state update with mapping, source peek should show C++ code."""
        tmp = _make_tmp_cpp("int main() {\n    return 42;\n}\n")
        engine = FakeEngine(tmp)
        engine.state.source_lines = ["int main() {", "    return 42;", "}"]
        engine.state.asm_content = "push rbp\nmov rbp, rsp\nmov eax, 42\npop rbp\nret"
        engine.state.asm_mapping = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            from localbolt.ui.source_peek import SourcePeekPanel
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                sp = pilot.app.query_one("#source-peek", SourcePeekPanel)
                # The peek should have been given the mapping
                assert sp._source_lines == ["int main() {", "    return 42;", "}"]
                assert sp._asm_mapping == {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_source_peek_show_for_line(self):
        """SourcePeekPanel.show_for_asm_line should display the panel when mapping exists."""
        tmp = _make_tmp_cpp("int main() {\n    return 42;\n}\n")
        engine = FakeEngine(tmp)
        engine.state.source_lines = ["int main() {", "    return 42;", "}"]
        engine.state.asm_content = "push rbp\nmov rbp, rsp\nmov eax, 42\npop rbp\nret"
        engine.state.asm_mapping = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            from localbolt.ui.source_peek import SourcePeekPanel
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                sp = pilot.app.query_one("#source-peek", SourcePeekPanel)
                sp.show_for_asm_line(3)
                # Panel should be visible when a valid mapping exists
                assert sp.display is True
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_source_peek_empty_mapping(self):
        """With no mapping, source peek should be hidden."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.source_lines = []
        engine.state.asm_mapping = {}
        engine.state.asm_content = ""
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            from localbolt.ui.source_peek import SourcePeekPanel
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                sp = pilot.app.query_one("#source-peek", SourcePeekPanel)
                sp.update_context(source_lines=[], asm_mapping={})
                sp.show_for_asm_line(1)
                # Panel should be hidden when no mapping is available
                assert sp.display is False
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)


# ────────────────────────────────────────────────────────────
# run_tui function test
# ────────────────────────────────────────────────────────────
class TestRunTui:
    """Test the run_tui entry point."""

    def test_run_tui_creates_app(self):
        """run_tui should create a LocalBoltApp and call run()."""
        fakes, cleanup = _inject_fakes()
        try:
            with patch("localbolt.ui.app.LocalBoltApp") as MockApp:
                mock_instance = MagicMock()
                MockApp.return_value = mock_instance
                from localbolt.ui.app import run_tui
                run_tui("/tmp/test.cpp")
                MockApp.assert_called_once_with("/tmp/test.cpp")
                mock_instance.run.assert_called_once()
        finally:
            cleanup()
