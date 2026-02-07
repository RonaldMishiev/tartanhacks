"""
Member C — Custom Widgets
=========================
Exposes: AssemblyView, StatusBar

The UI displays only the compiled assembly output.  The user edits
their C++ file in their own IDE; Watchdog detects saves and the
assembly view updates live.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class AssemblyView(Static):
    """
    Main pane — shows the compiled assembly output.
    ID: #assembly-view
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(id="assembly-view", **kwargs)

    def set_asm(self, highlighted) -> None:
        """Update the assembly pane with a Rich renderable."""
        self.update(highlighted)


class StatusBar(Static):
    """
    Bottom bar — current file, flags, compile status, error count.
    ID: #status-bar
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(id="status-bar", **kwargs)
        self._file: str = ""
        self._flags: str = ""
        self._status: str = "idle"
        self._errors: int = 0

    def set_status(
        self,
        *,
        file: str | None = None,
        flags: str | None = None,
        status: str | None = None,
        errors: int | None = None,
    ) -> None:
        if file is not None:
            self._file = file
        if flags is not None:
            self._flags = flags
        if status is not None:
            self._status = status
        if errors is not None:
            self._errors = errors
        self._render_bar()

    def _render_bar(self) -> None:
        parts = []
        if self._file:
            parts.append(f"📄 {self._file}")
        if self._flags:
            parts.append(f"⚙  {self._flags}")
        parts.append(f"● {self._status}")
        if self._errors:
            parts.append(f"❌ {self._errors} error(s)")
        self.update("  │  ".join(parts))
