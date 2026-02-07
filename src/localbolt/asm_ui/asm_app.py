from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import VerticalScroll
from textual.binding import Binding

try:
    from ..utils.highlighter import highlight_asm_line, severity_styles
except ImportError:
    import sys
    _src = Path(__file__).resolve().parents[2]
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
    from localbolt.utils.highlighter import highlight_asm_line, severity_styles

DEFAULT_ASM = Path(__file__).parent / "test_assembly.txt"
GUTTER_WIDTH = 6
CURSOR_WIDTH = 2  # "▶ " or "  "


def _severity_class(cycles: int | None) -> str:
    """Map cycle count to a CSS class name for full-width background tint."""
    if cycles is None:
        return ""
    if cycles <= 1:
        return "sev-low"
    if cycles <= 4:
        return "sev-med"
    return "sev-high"


class AsmLine(Static):
    """A single assembly line widget."""


class AsmApp(App):
    """Minimal Textual UI for viewing syntax-highlighted assembly with a line cursor."""

    CSS = """
    Screen { background: #1e1e1e; }
    #asm-scroll { height: 1fr; }
    AsmLine { width: 100%; height: 1; }
    AsmLine.sev-low  { background: #103010; }
    AsmLine.sev-med  { background: #302510; }
    AsmLine.sev-high { background: #301010; }
    AsmLine.cursor   { background: #264f78; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("j", "cursor_down", show=False),
    ]

    def __init__(self, asm_file: str | Path = DEFAULT_ASM, cycle_counts: dict[int, int] | None = None):
        super().__init__()
        self.asm_file = Path(asm_file)
        self.cycle_counts = cycle_counts or {}
        self._cursor = 0
        self._lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="asm-scroll")
        yield Footer()

    def on_mount(self) -> None:
        self._load_asm()
        self.call_after_refresh(self._refresh_all_lines)

    def on_resize(self) -> None:
        self._refresh_all_lines()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _get_width(self) -> int:
        """Return the usable width of the scroll container."""
        try:
            w = self.query_one("#asm-scroll").content_size.width
            return w if w > 0 else self.size.width or 80
        except Exception:
            return 80

    def _render_line(self, idx: int) -> Text:
        """Build Rich Text for a single line: cursor indicator + asm + gutter."""
        line = self._lines[idx]
        line_num = idx + 1
        cycles = self.cycle_counts.get(line_num)
        fg, _ = severity_styles(cycles)
        width = self._get_width()

        row = Text()

        # Left-side cursor indicator
        if idx == self._cursor:
            row.append("▶ ", style="bold cyan")
        else:
            row.append("  ")

        # Syntax-highlighted assembly (no inline bg — CSS handles background)
        row.append_text(highlight_asm_line(line, ""))

        # Pad to push gutter to the far right edge
        gutter_text = f"{cycles}" if cycles is not None else ""
        used = CURSOR_WIDTH + len(line) + len(gutter_text)
        padding = max(1, width - used)
        row.append(" " * padding)

        # Gutter cycle count
        if cycles is not None:
            row.append(gutter_text, style=fg)

        return row

    def _load_asm(self) -> None:
        """Read the assembly file and populate line widgets."""
        self._lines = self.asm_file.read_text().splitlines()
        self._cursor = 0
        scroll = self.query_one("#asm-scroll")
        scroll.remove_children()

        for i in range(len(self._lines)):
            widget = AsmLine(self._render_line(i), id=f"asm-line-{i}")
            sev = _severity_class(self.cycle_counts.get(i + 1))
            if sev:
                widget.add_class(sev)
            if i == self._cursor:
                widget.add_class("cursor")
            scroll.mount(widget)

    def _refresh_all_lines(self) -> None:
        """Re-render every line (e.g. after terminal resize)."""
        for i in range(len(self._lines)):
            try:
                self.query_one(f"#asm-line-{i}", AsmLine).update(self._render_line(i))
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Cursor movement
    # ------------------------------------------------------------------

    def _move_cursor(self, new: int) -> None:
        if new < 0 or new >= len(self._lines):
            return
        old = self._cursor
        self._cursor = new

        old_w = self.query_one(f"#asm-line-{old}", AsmLine)
        old_w.remove_class("cursor")
        old_w.update(self._render_line(old))

        new_w = self.query_one(f"#asm-line-{new}", AsmLine)
        new_w.add_class("cursor")
        new_w.update(self._render_line(new))
        new_w.scroll_visible()

    def action_cursor_up(self) -> None:
        self._move_cursor(self._cursor - 1)

    def action_cursor_down(self) -> None:
        self._move_cursor(self._cursor + 1)

    def action_refresh(self) -> None:
        self._load_asm()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_line(self) -> str:
        """Return the raw assembly text of the currently selected line."""
        if self._lines:
            return self._lines[self._cursor]
        return ""


def run_asm_app(asm_file: str | Path = DEFAULT_ASM, cycle_counts: dict[int, int] | None = None):
    AsmApp(asm_file, cycle_counts).run()


if __name__ == "__main__":
    sample_cycles = {1: 1, 2: 1, 3: 3, 4: 1, 5: 1, 6: 2, 7: 6, 8: 1, 9: 1}
    run_asm_app(cycle_counts=sample_cycles)
