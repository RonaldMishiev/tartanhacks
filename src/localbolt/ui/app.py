from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from ..engine import BoltEngine
from ..utils.state import LocalBoltState
from ..utils.highlighter import build_gutter, INSTRUCTIONS

class LocalBoltApp(App):
    """The main LocalBolt TUI with full-width highlighting."""

    CSS = """
    Screen { background: #1e1e1e; }
    #asm-container { height: 1fr; width: 1fr; }
    #asm-view { width: 200; height: auto; }
    #error-view { color: #ff5555; display: none; }
    .panel-title {
        background: $primary;
        color: white;
        text-align: center;
    }
    .error-title { background: #a80000; color: white; text-align: center; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Recompile", show=True),
    ]

    class StateUpdated(Message):
        def __init__(self, state: LocalBoltState) -> None:
            super().__init__()
            self.state = state

    def __init__(self, source_file: str):
        super().__init__()
        self.engine = BoltEngine(source_file)
        self.engine.on_update_callback = lambda state: self.post_message(self.StateUpdated(state))

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(" ASSEMBLY OUTPUT ", id="main-title", classes="panel-title"),
            VerticalScroll(
                Static(id="asm-view"), 
                TextArea(id="error-view", read_only=True),
                id="asm-container"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.engine.start()

    def on_local_bolt_app_state_updated(self, message: StateUpdated) -> None:
        state = message.state
        asm_view = self.query_one("#asm-view", Static)
        error_view = self.query_one("#error-view", TextArea)
        title = self.query_one("#main-title", Static)

        if state.has_errors:
            asm_view.display = False
            error_view.display = True
            error_view.text = state.compiler_output
            title.update(" COMPILATION ERROR ")
            title.set_class(True, "error-title")
        else:
            error_view.display = False
            asm_view.display = True
            
            # ALIGNMENT LOGIC: Map llvm-mca stats to actual instructions only
            asm_lines = state.asm_content.splitlines()
            aligned_cycle_counts = {}
            instr_idx = 0
            
            for line_idx, line in enumerate(asm_lines):
                stripped = line.strip()
                # Use the shared INSTRUCTIONS regex to identify real code lines
                if stripped and not stripped.endswith(":") and INSTRUCTIONS.search(stripped):
                    if instr_idx in state.perf_stats:
                        aligned_cycle_counts[line_idx + 1] = state.perf_stats[instr_idx].latency
                    instr_idx += 1
            
            title.update(f" ASSEMBLY OUTPUT | {len(state.perf_stats)} instructions analyzed ")
            title.set_class(True, "panel-title")
            
            # Pass width to build_gutter to ensure background spans the whole pane
            rendered_asm = build_gutter(asm_lines, aligned_cycle_counts, width=150)
            asm_view.update(rendered_asm)

    def action_refresh(self) -> None:
        self.engine.refresh()

    def on_unmount(self) -> None:
        self.engine.stop()

def run_tui(source_file: str):
    app = LocalBoltApp(source_file)
    app.run()
