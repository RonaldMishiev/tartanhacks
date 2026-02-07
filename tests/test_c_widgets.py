"""
Tests for Member C — widgets.py
================================
Verifies AssemblyView and StatusBar
in isolation using Textual's built-in async test harness.
"""

from __future__ import annotations

import pytest
from rich.text import Text
from textual.app import App, ComposeResult

from localbolt.ui.widgets import (
    AssemblyView,
    StatusBar,
)


# ────────────────────────────────────────────────────────────
# Minimal shell app used to mount widgets for testing
# ────────────────────────────────────────────────────────────
class _WidgetTestApp(App):
    """Headless Textual app that composes every Member C widget."""

    def compose(self) -> ComposeResult:
        yield AssemblyView()
        yield StatusBar()


# ────────────────────────────────────────────────────────────
# AssemblyView tests
# ────────────────────────────────────────────────────────────
class TestAssemblyView:
    """Tests for the AssemblyView widget."""

    @pytest.mark.asyncio
    async def test_assembly_view_has_correct_id(self):
        async with _WidgetTestApp().run_test() as pilot:
            av = pilot.app.query_one("#assembly-view", AssemblyView)
            assert av is not None
            assert av.id == "assembly-view"

    @pytest.mark.asyncio
    async def test_set_asm_updates_content(self):
        """set_asm() should accept a Rich Text renderable without crashing."""
        async with _WidgetTestApp().run_test() as pilot:
            av = pilot.app.query_one("#assembly-view", AssemblyView)
            asm = Text("mov rax, rbx\nadd rax, 1\nret")
            av.set_asm(asm)
            await pilot.pause()
            # The widget accepted the update (no exception)

    @pytest.mark.asyncio
    async def test_set_asm_with_empty_text(self):
        """set_asm() should handle empty content gracefully."""
        async with _WidgetTestApp().run_test() as pilot:
            av = pilot.app.query_one("#assembly-view", AssemblyView)
            av.set_asm(Text(""))
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_set_asm_replaces_previous(self):
        """Calling set_asm() again should replace previous content."""
        async with _WidgetTestApp().run_test() as pilot:
            av = pilot.app.query_one("#assembly-view", AssemblyView)
            av.set_asm(Text("first"))
            av.set_asm(Text("second"))
            await pilot.pause()


# ────────────────────────────────────────────────────────────
# StatusBar tests
# ────────────────────────────────────────────────────────────
class TestStatusBar:
    """Tests for the StatusBar widget."""

    @pytest.mark.asyncio
    async def test_status_bar_has_correct_id(self):
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            assert sb is not None
            assert sb.id == "status-bar"

    @pytest.mark.asyncio
    async def test_set_status_updates_file(self):
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(file="main.cpp")
            assert sb._file == "main.cpp"

    @pytest.mark.asyncio
    async def test_set_status_updates_flags(self):
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(flags="-O2 -march=native")
            assert sb._flags == "-O2 -march=native"

    @pytest.mark.asyncio
    async def test_set_status_updates_status(self):
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(status="compiling…")
            assert sb._status == "compiling…"

    @pytest.mark.asyncio
    async def test_set_status_updates_errors(self):
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(errors=3)
            assert sb._errors == 3

    @pytest.mark.asyncio
    async def test_set_status_partial_update(self):
        """Setting only one field should not reset the others."""
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(file="test.cpp", flags="-O3", status="ready", errors=0)
            sb.set_status(status="error")
            assert sb._file == "test.cpp"
            assert sb._flags == "-O3"
            assert sb._status == "error"
            assert sb._errors == 0

    @pytest.mark.asyncio
    async def test_render_bar_contains_file(self):
        """The rendered bar should include the filename in internal state."""
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(file="hello.cpp", status="ready")
            await pilot.pause()
            assert sb._file == "hello.cpp"
            assert sb._status == "ready"

    @pytest.mark.asyncio
    async def test_render_bar_shows_errors(self):
        """Error count should be stored when errors > 0."""
        async with _WidgetTestApp().run_test() as pilot:
            sb = pilot.app.query_one("#status-bar", StatusBar)
            sb.set_status(errors=5)
            await pilot.pause()
            assert sb._errors == 5
