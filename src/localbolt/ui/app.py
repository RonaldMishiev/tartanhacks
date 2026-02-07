from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import VerticalScroll, Horizontal, Vertical, Container
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
from ..engine import BoltEngine
from ..utils.state import LocalBoltState
from ..utils.highlighter import build_gutter, highlight_asm_line, severity_styles, INSTRUCTIONS
from .source_peek import SourcePeekPanel
from .instruction_help import InstructionHelpPanel
from .flags_palette import FlagsPopup

# User Palette
C_BG = "#EBEEEE"
C_TEXT = "#191A1A"
C_ACCENT1 = "#45d3ee" # Cyan
C_ACCENT2 = "#9FBFC5" # Muted Blue
C_ACCENT3 = "#94bfc1" # Teal
C_ACCENT4 = "#fecd91" # Orange

def _severity_class(cycles: int | None) -> str:
    if cycles is None: return ""
    if cycles <= 1: return "sev-low"
    if cycles <= 4: return "sev-med"
    return "sev-high"

class AsmLine(Static): pass
class AsmScroll(VerticalScroll): BINDINGS = []

class LocalBoltApp(App):
    """Modern Assembly Explorer with Dual Floating Popups."""

    CSS = f"""
    Screen {{ 
        background: {C_BG}; 
        color: {C_TEXT};
        layers: base popups;
        align: center middle;
    }}
    
    #main-layout {{
        height: 1fr;
        width: 100%;
        layer: base;
    }}

    #asm-container-outer {{ 
        height: 1fr; 
        width: 100%; 
        border: solid {C_ACCENT2};
        background: {C_BG};
        margin: 1 1;
    }}

    #asm-container {{ height: 1fr; width: 1fr; }}
    
    #error-view {{ color: #a80000; display: none; margin: 1 2; }}
    
    SourcePeekPanel {{ layer: popups; }}
    InstructionHelpPanel {{ layer: popups; }}
    FlagsPopup {{ 
        display: none;
        layer: popups;
        margin: 1 1;
        width: 60;
    }}
    
    AsmLine {{ width: 100%; height: 1; }}
    AsmLine.sev-low  {{ background: #d1e7dd; }}
    AsmLine.sev-med  {{ background: #fff3cd; }}
    AsmLine.sev-high {{ background: #f8d7da; }}
    AsmLine.cursor   {{ background: {C_ACCENT2}; }}
    
    Footer {{ background: {C_TEXT}; color: {C_ACCENT1}; }}
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Recompile", show=True),
        Binding("o", "toggle_flags", "Flags", show=True),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("k", "cursor_up", show=False, priority=True),
        Binding("j", "cursor_down", show=False, priority=True),
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
        self._asm_mapping: dict[int, int] = {}  # asm_line_idx -> source_line_number
        self._sibling_lines: set[int] = set()   # asm indices sharing the same C++ line as cursor

    def compose(self) -> ComposeResult:
        with Vertical(id="main-layout"):
            yield TextArea(id="error-view", read_only=True)
            yield Vertical(
                AsmScroll(id="asm-container"),
                id="asm-container-outer"
            )
        # Dual Floating Popups
        yield SourcePeekPanel(id="source-peek")
        yield InstructionHelpPanel(id="instr-help")
        yield FlagsPopup(id="flags-palette")
        yield Footer()

    def on_mount(self) -> None:
        self.engine.start()

    def _render_line(self, idx: int) -> Text:
        if idx >= len(self._asm_lines): return Text("")
        line = self._asm_lines[idx]
        line_num = idx + 1
        cycles = self._cycle_counts.get(line_num)
        fg, _ = severity_styles(cycles)
        width = 200 
        row = Text()
        # Gutter indicator: cursor ▶, sibling │, or blank
        if idx == self._cursor:
            row.append("▶ ", style=f"bold {C_ACCENT4}")
        elif idx in self._sibling_lines:
            row.append("│ ", style=f"bold {C_ACCENT1}")
        else:
            row.append("  ")
        row.append_text(highlight_asm_line(line, ""))
        gutter_text = f"{cycles}c" if cycles is not None else ""
        used = 2 + len(line) + len(gutter_text)
        padding = max(1, width - used)
        row.append(" " * padding)
        if cycles is not None: row.append(gutter_text, style=fg)
        return row

    def _populate_asm_lines(self) -> None:
        scroll = self.query_one("#asm-container", AsmScroll)
        scroll.query(AsmLine).remove()
        self._generation = getattr(self, "_generation", 0) + 1
        widgets = []
        for i in range(len(self._asm_lines)):
            widget = AsmLine(self._render_line(i), id=f"asm-line-{self._generation}-{i}")
            sev = _severity_class(self._cycle_counts.get(i + 1))
            if sev: widget.add_class(sev)
            if i == self._cursor: widget.add_class("cursor")
            widgets.append(widget)
        if widgets: scroll.mount(*widgets)

    def _compute_siblings(self) -> set[int]:
        """Find all asm line indices that map to the same C++ source line as the cursor."""
        cursor_src = self._asm_mapping.get(self._cursor)
        if cursor_src is None:
            return set()
        return {
            idx for idx, src in self._asm_mapping.items()
            if src == cursor_src and idx != self._cursor
        }

    def _move_cursor(self, new: int) -> None:
        if new < 0 or new >= len(self._asm_lines): return
        old, self._cursor = self._cursor, new
        gen = getattr(self, "_generation", 0)

        # Collect lines that need re-rendering: old siblings, old cursor, new siblings, new cursor
        old_siblings = self._sibling_lines
        self._sibling_lines = self._compute_siblings()
        dirty = {old} | old_siblings | {new} | self._sibling_lines

        for idx in dirty:
            try:
                w = self.query_one(f"#asm-line-{gen}-{idx}", AsmLine)
                if idx == new:
                    w.add_class("cursor")
                else:
                    w.remove_class("cursor")
                w.update(self._render_line(idx))
                if idx == new:
                    w.scroll_visible()
            except Exception:
                pass

        self._sync_peek()

    def action_cursor_up(self) -> None: self._move_cursor(self._cursor - 1)
    def action_cursor_down(self) -> None: self._move_cursor(self._cursor + 1)

    def action_refresh(self) -> None:
        self.engine.refresh()

    def action_toggle_flags(self) -> None:
        current = " ".join(self.engine.user_flags)
        self.query_one("#flags-palette", FlagsPopup).show(current)

    def on_flags_popup_flags_changed(self, message: FlagsPopup.FlagsChanged) -> None:
        new_flags = message.flags.split()
        self.engine.set_flags(new_flags)

    def on_local_bolt_app_state_updated(self, message: StateUpdated) -> None:
        state = message.state
        error_view, scroll = self.query_one("#error-view", TextArea), self.query_one("#asm-container", AsmScroll)
        if state.has_errors:
            scroll.display, error_view.display = False, True
            error_view.text = state.compiler_output
        else:
            scroll.display, error_view.display = True, False
            self._asm_lines = state.asm_content.splitlines()
            self._cycle_counts = {}
            instr_idx = 0
            for line_idx, line in enumerate(self._asm_lines):
                stripped = line.strip()
                if stripped and not stripped.endswith(":") and INSTRUCTIONS.search(stripped):
                    if instr_idx in state.perf_stats:
                        self._cycle_counts[line_idx + 1] = state.perf_stats[instr_idx].latency
                    instr_idx += 1
            self._populate_asm_lines()
        
        self._asm_mapping = state.asm_mapping
        self._sibling_lines = self._compute_siblings()
        self.query_one("#source-peek", SourcePeekPanel).update_context(state.source_lines, state.asm_mapping)
        self._sync_peek()

    def _sync_peek(self) -> None:
        try:
            # Sync Source Peek
            self.query_one("#source-peek", SourcePeekPanel).show_for_asm_line(self._cursor)
            
            # Sync Instruction Help
            instr_help = self.query_one("#instr-help", InstructionHelpPanel)
            if 0 <= self._cursor < len(self._asm_lines):
                instr_help.show_for_asm_line(self._asm_lines[self._cursor])
        except Exception: pass

    def on_unmount(self) -> None: self.engine.stop()

def run_tui(source_file: str):
    app = LocalBoltApp(source_file)
    app.run()
