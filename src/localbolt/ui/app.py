"""
Member C — Main Textual Application
====================================
Owns the master pipeline: compile → map → highlight → display.
Watches the source file for changes via Watchdog.

The UI displays only the assembly output.  The user edits their
C++ file in their own IDE; saves are detected by Watchdog and
the assembly view updates automatically.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.widgets import Header
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from localbolt.ui.widgets import (
    AssemblyView,
    StatusBar,
)

# Lazy-import path strings for teammates' modules (may still be stubs)
_DRIVER = "localbolt.compiler.driver"
_MAPPER = "localbolt.parsing.mapper"
_HIGHLIGHTER = "localbolt.utils.highlighter"
_CONFIG = "localbolt.utils.config"


# ────────────────────────────────────────────────────────────
# File-change handler (Watchdog → Textual bridge)
# ────────────────────────────────────────────────────────────
class _SourceFileHandler(FileSystemEventHandler):
    """Watchdog handler that posts a callback into the Textual event loop."""

    def __init__(self, app: "LocalBoltApp", watched_path: str) -> None:
        super().__init__()
        self._app = app
        self._watched = Path(watched_path).resolve()

    def on_modified(self, event: FileModifiedEvent) -> None:  # type: ignore[override]
        if Path(event.src_path).resolve() == self._watched:
            # Schedule the async handler on the Textual event loop
            self._app.call_from_thread(self._app.trigger_recompile)


# ────────────────────────────────────────────────────────────
# The App
# ────────────────────────────────────────────────────────────
class LocalBoltApp(App):
    """LocalBolt — a local Compiler Explorer in your terminal."""

    CSS_PATH = "styles.tcss"
    TITLE = "LocalBolt"

    def __init__(self, source_file: str, flags: list[str] | None = None) -> None:
        super().__init__()
        self.source_file: str = str(Path(source_file).resolve())
        self.flags: list[str] = flags or ["-O0"]
        self.current_mapping = None
        self._observer: Optional[Observer] = None  # type: ignore[valid-type]

    # -- compose the widget tree ----------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield AssemblyView()
        yield StatusBar()

    # -- lifecycle ------------------------------------------------

    async def on_mount(self) -> None:
        self.status_bar.set_status(
            file=Path(self.source_file).name,
            flags=" ".join(self.flags),
            status="watching",
        )
        # Start watching for saves
        self._start_watcher()
        # Initial compile
        await self.on_file_changed(self.source_file)

    def on_unmount(self) -> None:
        self._stop_watcher()

    # -- convenience accessors ------------------------------------

    @property
    def assembly_view(self) -> AssemblyView:
        return self.query_one("#assembly-view", AssemblyView)

    @property
    def status_bar(self) -> StatusBar:
        return self.query_one("#status-bar", StatusBar)

    # -- watcher --------------------------------------------------

    def _start_watcher(self) -> None:
        handler = _SourceFileHandler(self, self.source_file)
        self._observer = Observer()
        self._observer.schedule(
            handler,
            path=str(Path(self.source_file).parent),
            recursive=False,
        )
        self._observer.daemon = True
        self._observer.start()

    def _stop_watcher(self) -> None:
        if self._observer is not None:
            self._observer.stop()

    # -- public entry point for recompile -------------------------

    def trigger_recompile(self) -> None:
        """Called from the Watchdog thread via call_from_thread."""
        asyncio.ensure_future(self.on_file_changed(self.source_file))

    # ============================================================
    # MASTER PIPELINE  (compile → map → highlight → display)
    # ============================================================

    async def on_file_changed(self, file_path: str) -> None:
        """
        The master pipeline.  Called on launch and every time the
        watched source file is saved.
        """
        import importlib

        self.status_bar.set_status(status="compiling…")

        # --- 1. Compile (Member A) --------------------------------
        try:
            driver = importlib.import_module(_DRIVER)
            result = driver.compile_source(file_path, self.flags)
        except Exception as exc:
            self._show_error(f"Compile error: {exc}")
            return

        if not result.success:
            self._show_error(result.stderr)
            return

        # --- 2. Map (Member B) ------------------------------------
        try:
            mapper = importlib.import_module(_MAPPER)
            mapping = mapper.parse_mapping(result.asm_content)
        except Exception as exc:
            self._show_error(f"Mapping error: {exc}")
            return

        # --- 3. Analyze (Member A — optional) ---------------------
        analysis = None
        try:
            driver = importlib.import_module(_DRIVER)
            analysis = driver.analyze_assembly(result.asm_content)
        except Exception:
            pass  # llvm-mca may not be installed; gracefully skip

        # --- 4. Highlight (Member D) ------------------------------
        try:
            highlighter = importlib.import_module(_HIGHLIGHTER)
            highlighted = highlighter.highlight_asm(mapping.cleaned_asm)
        except Exception:
            # Fallback: show raw cleaned asm
            from rich.text import Text

            highlighted = Text(mapping.cleaned_asm)

        # --- 5. Update UI -----------------------------------------
        self.assembly_view.set_asm(highlighted)

        # --- 6. Store mapping for scroll sync ---------------------
        self.current_mapping = mapping

        self.status_bar.set_status(status="ready", errors=0)

    # -- helpers ---------------------------------------------------

    def _show_error(self, text: str) -> None:
        self.status_bar.set_status(status="error", errors=1)
        self.assembly_view.set_asm(
            __import__("rich.text", fromlist=["Text"]).Text(
                text, style="bold red"
            )
        )
