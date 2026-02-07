"""
Tests for Member C — app.py
=============================
Tests the LocalBoltApp UI wiring logic with MOCKED engine/teammates.

The engine (BoltEngine) is completely mocked — these tests verify
that Member C's UI layer works correctly in isolation:
  - Widget tree composition (#asm-view, #perf-table, Header, Footer)
  - State update message handling
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
from textual.widgets import TextArea, DataTable


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
    hl_mod = types.ModuleType("localbolt.utils.highlighter")
    hl_mod.highlight_asm = MagicMock(return_value=None)
    hl_mod.build_gutter = MagicMock(return_value=None)

    # --- localbolt.compiler.driver ---
    driver_mod = types.ModuleType("localbolt.compiler.driver")
    driver_mod.CompilerDriver = MagicMock

    # --- localbolt.engine ---
    engine_mod = types.ModuleType("localbolt.engine")
    if engine_instance is not None:
        engine_mod.BoltEngine = lambda source_file: engine_instance
    else:
        engine_mod.BoltEngine = FakeEngine

    fakes = {
        "localbolt.parsing.perf_parser": pp_mod,
        "localbolt.parsing.diagnostics": diag_mod,
        "localbolt.parsing": parsing_mod,
        "localbolt.utils.state": state_mod,
        "localbolt.utils.watcher": watcher_mod,
        "localbolt.utils.highlighter": hl_mod,
        "localbolt.compiler.driver": driver_mod,
        "localbolt.engine": engine_mod,
    }

    for name, mod in fakes.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod

    # Force reimport of app.py so it picks up the fakes
    sys.modules.pop("localbolt.ui.app", None)

    def cleanup():
        sys.modules.pop("localbolt.ui.app", None)
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
    async def test_app_has_asm_view(self):
        """App should have a TextArea with id='asm-view'."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                av = pilot.app.query_one("#asm-view", TextArea)
                assert av is not None
                assert av.read_only is True
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_app_has_perf_table(self):
        """App should have a DataTable with id='perf-table'."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                pt = pilot.app.query_one("#perf-table", DataTable)
                assert pt is not None
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
    async def test_app_has_header_and_footer(self):
        """App should have Header and Footer widgets."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                from textual.widgets import Header, Footer
                assert pilot.app.query_one(Header) is not None
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
    async def test_asm_view_gets_content_on_state_update(self):
        """After engine state update, the asm-view TextArea should have content."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.asm_content = "push rbp\nmov rbp, rsp\npop rbp\nret"
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                asm_view = pilot.app.query_one("#asm-view", TextArea)
                assert "push rbp" in asm_view.text
                assert "ret" in asm_view.text
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
    async def test_perf_table_populated_on_update(self):
        """After a state update with perf_stats, the DataTable should have rows."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.perf_stats = {
            1: FakeInstructionStats(latency=2),
            2: FakeInstructionStats(latency=5),
        }
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                pt = pilot.app.query_one("#perf-table", DataTable)
                assert pt.row_count == 2
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_empty_asm_clears_view(self):
        """If engine returns empty asm, the asm-view should be empty."""
        tmp = _make_tmp_cpp()
        engine = FakeEngine(tmp)
        engine.state.asm_content = ""
        fakes, cleanup = _inject_fakes(engine_instance=engine)
        try:
            from localbolt.ui.app import LocalBoltApp
            app = LocalBoltApp(source_file=tmp)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                asm_view = pilot.app.query_one("#asm-view", TextArea)
                assert asm_view.text == ""
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

        try:
            from localbolt.ui.app import LocalBoltApp
            with pytest.raises(RuntimeError, match="Engine not available"):
                app = LocalBoltApp(source_file=tmp)
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
