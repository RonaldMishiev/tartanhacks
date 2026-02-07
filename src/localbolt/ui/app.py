from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
from ..engine import BoltEngine
from ..utils.state import LocalBoltState
from ..utils.highlighter import build_gutter, highlight_asm_line, severity_styles, INSTRUCTIONS
from .source_peek import SourcePeekPanel

from rich.text import Text


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
    """A single assembly line widget for per-line cursor navigation."""


class AsmScroll(VerticalScroll):
    """VerticalScroll with up/down disabled so the App handles cursor movement."""
    BINDINGS = []  # Clear inherited up/down/pgup/pgdown bindings


# User Palette
C_BG = "#EBEEEE"
C_TEXT = "#191A1A"
C_ACCENT1 = "#45d3ee" # Cyan
C_ACCENT2 = "#9FBFC5" # Muted Blue
C_ACCENT3 = "#94bfc1" # Teal
C_ACCENT4 = "#fecd91" # Orange

class MosaicHeader(Static):
    """A header with a horizontal gradient to match the Mosaic theme."""
    def render(self) -> Text:
        text = " LOCALBOLT " + " " * 120
        rich_text = Text(text, style="bold italic")
        
        # Gradient between the misc colors
        start = (69, 211, 238) # #45d3ee
        end = (159, 191, 197)   # #9FBFC5
        
        for i in range(len(text)):
            ratio = i / len(text)
            r = int(start[0] + (end[0] - start[0]) * ratio)
            g = int(start[1] + (end[1] - start[1]) * ratio)
            b = int(start[2] + (end[2] - start[2]) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            rich_text.stylize(color, i, i+1)
            
        return rich_text

class LocalBoltApp(App):
    """Modern, Light-Themed Mosaic LocalBolt TUI."""

    CSS = f"""
    Screen {{ 
        background: {C_BG}; 
        color: {C_TEXT};
    }}
    
    MosaicHeader {{
        height: 1;
        background: {C_TEXT};
        width: 100%;
    }}

    #asm-container {{ 
        height: 1fr; 
        width: 1fr; 
        border: solid {C_ACCENT2};
        background: {C_BG};
        margin: 1 2;
    }}
    
    #error-view {{ color: #a80000; display: none; margin: 1 2; }}
    
    .panel-title {{
        color: {C_ACCENT3};
        text-align: center;
        margin-top: 1;
    }}
    
    #source-peek {{ height: 5; dock: bottom; background: {C_TEXT}; border-top: solid {C_ACCENT2}; padding: 0 1; }}
    AsmLine {{ width: 100%; height: 1; }}
    AsmLine.sev-low  {{ background: #d1e7dd; }}
    AsmLine.sev-med  {{ background: #fff3cd; }}
    AsmLine.sev-high {{ background: #f8d7da; }}
    AsmLine.cursor   {{ background: {C_ACCENT2}; }}
    
    Footer {{
        background: {C_TEXT};
        color: {C_ACCENT1};
    }}
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Recompile", show=True),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("k", "cursor_up", show=False, priority=True),
        Binding("j", "cursor_down", show=False, priority=True),
        Binding("pageup", "cursor_page_up", show=False, priority=True),
        Binding("pagedown", "cursor_page_down", show=False, priority=True),
    ]

    class StateUpdated(Message):
        def __init__(self, state: LocalBoltState) -> None:
            super().__init__()
            self.state = state

    def __init__(self, source_file: str):
        super().__init__()
        self.engine = BoltEngine(source_file)
        self.engine.on_update_callback = lambda state: self.post_message(self.StateUpdated(state))
        self._cursor = 0
        self._asm_lines: list[str] = []
        self._cycle_counts: dict[int, int] = {}

    def compose(self) -> ComposeResult:
        yield MosaicHeader()
        yield Static(" ASSEMBLY EXPLORER ", id="main-title", classes="panel-title")
        yield Vertical(
            TextArea(id="error-view", read_only=True),
            AsmScroll(id="asm-container")
        )
        yield SourcePeekPanel(id="source-peek")
        yield Footer()

    def on_mount(self) -> None:
        self._last_state: LocalBoltState | None = None
        self.engine.start()
        peek = self.query_one("#source-peek", SourcePeekPanel)
        peek.show_for_asm_line(1)

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _get_width(self) -> int:
        try:
            w = self.query_one("#asm-container").content_size.width
            return w if w > 0 else self.size.width or 80
        except Exception:
            return 80

    def _render_line(self, idx: int) -> Text:
        """Build Rich Text for a single asm line with cursor + gutter."""
        line = self._asm_lines[idx]
        line_num = idx + 1
        cycles = self._cycle_counts.get(line_num)
        fg, _ = severity_styles(cycles)
        width = self._get_width()

        row = Text()

        # Cursor indicator
        if idx == self._cursor:
            row.append("▶ ", style="bold cyan")
        else:
            row.append("  ")

        # Syntax-highlighted assembly (no inline bg — CSS handles background)
        row.append_text(highlight_asm_line(line, ""))

        # Pad to push gutter to far right
        gutter_text = f"{cycles}c" if cycles is not None else ""
        used = 2 + len(line) + len(gutter_text)
        padding = max(1, width - used)
        row.append(" " * padding)

        # Gutter cycle count
        if cycles is not None:
            row.append(gutter_text, style=fg)

        return row

    def _populate_asm_lines(self) -> None:
        """Replace the scroll container content with per-line AsmLine widgets."""
        scroll = self.query_one("#asm-container", AsmScroll)

        # Remove old widgets — query all AsmLine and remove them
        old_widgets = scroll.query(AsmLine)
        for w in old_widgets:
            w.remove()

        self._cursor = 0
        self._generation = getattr(self, "_generation", 0) + 1

        widgets = []
        for i in range(len(self._asm_lines)):
            widget = AsmLine(self._render_line(i), id=f"asm-line-{self._generation}-{i}")
            sev = _severity_class(self._cycle_counts.get(i + 1))
            if sev:
                widget.add_class(sev)
            if i == self._cursor:
                widget.add_class("cursor")
            widgets.append(widget)

        if widgets:
            scroll.mount(*widgets)

    # ------------------------------------------------------------------
    # Cursor movement
    # ------------------------------------------------------------------

    def _move_cursor(self, new: int) -> None:
        if new < 0 or new >= len(self._asm_lines):
            return
        old = self._cursor
        self._cursor = new
        gen = getattr(self, "_generation", 0)

        try:
            old_w = self.query_one(f"#asm-line-{gen}-{old}", AsmLine)
            old_w.remove_class("cursor")
            old_w.update(self._render_line(old))
        except Exception:
            pass

        try:
            new_w = self.query_one(f"#asm-line-{gen}-{new}", AsmLine)
            new_w.add_class("cursor")
            new_w.update(self._render_line(new))
            new_w.scroll_visible()
        except Exception:
            pass

        # Sync source peek to cursor position
        self._sync_peek()

    def action_cursor_up(self) -> None:
        self._move_cursor(self._cursor - 1)

    def action_cursor_down(self) -> None:
        self._move_cursor(self._cursor + 1)

    def action_cursor_page_up(self) -> None:
        self._move_cursor(max(0, self._cursor - 20))

    def action_cursor_page_down(self) -> None:
        self._move_cursor(min(len(self._asm_lines) - 1, self._cursor + 20))

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------

    def on_local_bolt_app_state_updated(self, message: StateUpdated) -> None:
        state = message.state
        error_view = self.query_one("#error-view", TextArea)
        title = self.query_one("#main-title", Static)

        scroll = self.query_one("#asm-container", AsmScroll)

        if state.has_errors:
            # Hide asm container, show error
            scroll.display = False
            error_view.display = True
            error_view.text = state.compiler_output
            title.update(" COMPILATION ERROR ")
            title.styles.color = "#a80000"
        else:
            error_view.display = False
            scroll.display = True

            # Build aligned cycle counts
            self._asm_lines = state.asm_content.splitlines()
            self._cycle_counts = {}
            instr_idx = 0

            for line_idx, line in enumerate(self._asm_lines):
                stripped = line.strip()
                if stripped and not stripped.endswith(":") and INSTRUCTIONS.search(stripped):
                    if instr_idx in state.perf_stats:
                        self._cycle_counts[line_idx + 1] = state.perf_stats[instr_idx].latency
                    instr_idx += 1

            title.update(f" ASSEMBLY EXPLORER | {len(state.perf_stats)} instructions analyzed ")
            title.styles.color = C_ACCENT3
            title.set_class(True, "panel-title")

            # Populate per-line widgets
            self._populate_asm_lines()

        # Update source peek
        peek = self.query_one("#source-peek", SourcePeekPanel)
        peek.update_context(state.source_lines, state.asm_mapping)
        self._sync_peek()
        self._last_state = state

    def action_refresh(self) -> None:
        self.engine.refresh()

    def _sync_peek(self) -> None:
        """Sync the source peek panel to the current cursor position."""
        try:
            peek = self.query_one("#source-peek", SourcePeekPanel)
            peek.show_for_asm_line(self._cursor + 1)
        except Exception:
            pass

    def on_unmount(self) -> None:
        self.engine.stop()

def run_tui(source_file: str):
    app = LocalBoltApp(source_file)
    app.run()
