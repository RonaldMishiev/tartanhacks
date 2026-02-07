"""
Tests for Member C — app.py
=============================
Tests the LocalBoltApp wiring logic with MOCKED teammate modules.
Member A, B, and D are fully faked so these tests run standalone.

The UI is assembly-only: no SourceView, no GutterColumn, no scroll sync.

NOTE: The Watchdog Observer is patched out in every async test so
that no real OS file-watcher threads are started (those threads
cause hangs under pytest).
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

from localbolt.ui.widgets import (
    AssemblyView,
    StatusBar,
)


# ────────────────────────────────────────────────────────────
# Patch helper — disable Watchdog so tests don't hang
# ────────────────────────────────────────────────────────────
_PATCH_WATCHER = patch(
    "localbolt.ui.app.Observer", new_callable=lambda: type(
        "FakeObserver",
        (),
        {
            "__init__": lambda self: None,
            "schedule": lambda self, *a, **kw: None,
            "start": lambda self: None,
            "stop": lambda self: None,
            "__setattr__": lambda self, k, v: object.__setattr__(self, k, v),
        },
    ),
)


# ────────────────────────────────────────────────────────────
# Fake dataclasses mimicking teammates' interfaces
# ────────────────────────────────────────────────────────────
@dataclass
class FakeCompileResult:
    success: bool = True
    asm_content: str = "mov rax, rbx\nret\n"
    stderr: str = ""
    flags_used: list[str] = field(default_factory=lambda: ["-O0"])


@dataclass
class FakeMappingResult:
    source_to_asm: dict[int, list[int]] = field(
        default_factory=lambda: {1: [1, 2], 2: [3]}
    )
    asm_to_source: dict[int, int] = field(
        default_factory=lambda: {1: 1, 2: 1, 3: 2}
    )
    cleaned_asm: str = "mov rax, rbx\nadd rax, 1\nret"
    cleaned_asm_lines: list[str] = field(
        default_factory=lambda: ["mov rax, rbx", "add rax, 1", "ret"]
    )


@dataclass
class FakeAnalysisResult:
    success: bool = True
    raw_output: str = ""
    cycle_counts: dict[int, int] = field(
        default_factory=lambda: {1: 1, 2: 3, 3: 1}
    )
    total_cycles: int = 5


# ────────────────────────────────────────────────────────────
# Build fake modules to inject into sys.modules
# ────────────────────────────────────────────────────────────
def _make_fake_driver(
    compile_result: FakeCompileResult | None = None,
    analysis_result: FakeAnalysisResult | None = None,
):
    """Return a fake 'localbolt.compiler.driver' module."""
    mod = types.ModuleType("localbolt.compiler.driver")
    mod.compile_source = MagicMock(
        return_value=compile_result or FakeCompileResult()
    )
    mod.analyze_assembly = MagicMock(
        return_value=analysis_result or FakeAnalysisResult()
    )
    return mod


def _make_fake_mapper(mapping_result: FakeMappingResult | None = None):
    """Return a fake 'localbolt.parsing.mapper' module."""
    mod = types.ModuleType("localbolt.parsing.mapper")
    mod.parse_mapping = MagicMock(
        return_value=mapping_result or FakeMappingResult()
    )
    return mod


def _make_fake_highlighter():
    """Return a fake 'localbolt.utils.highlighter' module."""
    mod = types.ModuleType("localbolt.utils.highlighter")
    mod.highlight_asm = MagicMock(
        return_value=Text("mov rax, rbx\nadd rax, 1\nret")
    )
    return mod


def _make_fake_config():
    """Return a fake 'localbolt.utils.config' module."""
    mod = types.ModuleType("localbolt.utils.config")
    return mod


def _inject_fakes(
    compile_result=None,
    analysis_result=None,
    mapping_result=None,
):
    """Inject all fake teammate modules into sys.modules. Returns cleanup fn."""
    fakes = {
        "localbolt.compiler": types.ModuleType("localbolt.compiler"),
        "localbolt.compiler.driver": _make_fake_driver(compile_result, analysis_result),
        "localbolt.parsing": types.ModuleType("localbolt.parsing"),
        "localbolt.parsing.mapper": _make_fake_mapper(mapping_result),
        "localbolt.utils": types.ModuleType("localbolt.utils"),
        "localbolt.utils.highlighter": _make_fake_highlighter(),
        "localbolt.utils.config": _make_fake_config(),
    }
    originals = {}
    for name, mod in fakes.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod

    # Clear importlib caches so import_module finds our fakes
    importlib.invalidate_caches()

    def cleanup():
        for name in fakes:
            if originals[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = originals[name]
        importlib.invalidate_caches()

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
# App composition tests
# ────────────────────────────────────────────────────────────
class TestAppComposition:
    """Verify the widget tree is assembled correctly."""

    @pytest.mark.asyncio
    async def test_app_has_assembly_view(self):
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    av = pilot.app.query_one("#assembly-view", AssemblyView)
                    assert av is not None
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_app_has_status_bar(self):
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    sb = pilot.app.query_one("#status-bar", StatusBar)
                    assert sb is not None
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_app_has_no_source_view(self):
        """SourceView should NOT be in the widget tree."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    results = pilot.app.query("#source-view")
                    assert len(results) == 0
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)


# ────────────────────────────────────────────────────────────
# App init tests
# ────────────────────────────────────────────────────────────
class TestAppInit:
    """Verify constructor stores values correctly."""

    def test_stores_source_file(self):
        from localbolt.ui.app import LocalBoltApp
        app = LocalBoltApp(source_file="/tmp/test.cpp", flags=["-O2"])
        assert app.source_file.endswith("test.cpp")

    def test_stores_flags(self):
        from localbolt.ui.app import LocalBoltApp
        app = LocalBoltApp(source_file="/tmp/test.cpp", flags=["-O3", "-ffast-math"])
        assert app.flags == ["-O3", "-ffast-math"]

    def test_default_flags(self):
        from localbolt.ui.app import LocalBoltApp
        app = LocalBoltApp(source_file="/tmp/test.cpp")
        assert app.flags == ["-O0"]

    def test_mapping_starts_none(self):
        from localbolt.ui.app import LocalBoltApp
        app = LocalBoltApp(source_file="/tmp/test.cpp")
        assert app.current_mapping is None


# ────────────────────────────────────────────────────────────
# Pipeline tests (mocked teammates)
# ────────────────────────────────────────────────────────────
class TestPipeline:
    """Test on_file_changed with mocked teammate modules."""

    @pytest.mark.asyncio
    async def test_successful_pipeline_stores_mapping(self):
        """After a successful compile, current_mapping should be set."""
        tmp = _make_tmp_cpp()
        mapping = FakeMappingResult()
        fakes, cleanup = _inject_fakes(mapping_result=mapping)
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()
                    assert pilot.app.current_mapping is not None
                    assert pilot.app.current_mapping.source_to_asm == mapping.source_to_asm
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_compile_failure_shows_error(self):
        """When compile_source returns success=False, status should be 'error'."""
        tmp = _make_tmp_cpp()
        bad_result = FakeCompileResult(success=False, stderr="undefined reference")
        fakes, cleanup = _inject_fakes(compile_result=bad_result)
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()
                    sb = pilot.app.query_one("#status-bar", StatusBar)
                    assert sb._status == "error"
                    assert sb._errors == 1
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_compile_calls_driver(self):
        """compile_source should be called with the file and flags."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O2"])
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()
                    driver = fakes["localbolt.compiler.driver"]
                    driver.compile_source.assert_called()
                    call_args = driver.compile_source.call_args
                    assert call_args[0][1] == ["-O2"]
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_mapper_called_with_asm(self):
        """parse_mapping should be called with the asm from compile_source."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()
                    mapper = fakes["localbolt.parsing.mapper"]
                    mapper.parse_mapping.assert_called()
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_highlighter_called(self):
        """highlight_asm should be called with the cleaned assembly."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()
                    hl = fakes["localbolt.utils.highlighter"]
                    hl.highlight_asm.assert_called()
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_status_ready_after_success(self):
        """After a successful pipeline, status should be 'ready'."""
        tmp = _make_tmp_cpp()
        fakes, cleanup = _inject_fakes()
        try:
            with _PATCH_WATCHER:
                from localbolt.ui.app import LocalBoltApp
                app = LocalBoltApp(source_file=tmp, flags=["-O0"])
                async with app.run_test(size=(120, 40)) as pilot:
                    await pilot.pause()
                    sb = pilot.app.query_one("#status-bar", StatusBar)
                    assert sb._status == "ready"
                    assert sb._errors == 0
        finally:
            cleanup()
            Path(tmp).unlink(missing_ok=True)
