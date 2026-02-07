from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from ..engine import BoltEngine
from ..utils.state import LocalBoltState
from ..utils.highlighter import build_gutter

class LocalBoltApp(App):
    """The main LocalBolt TUI, integrating the Asm Component logic."""

    CSS = """
    Screen { background: #1e1e1e; }
    #asm-container { height: 1fr; width: 1fr; }
    #asm-view { width: auto; height: auto; }
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
            # SWITCH TO ERROR MODE
            asm_view.display = False
            error_view.display = True
            error_view.text = state.compiler_output
            title.update(" COMPILATION ERROR ")
            title.set_class(True, "error-title")
            title.set_class(False, "panel-title")
        else:
            # SWITCH TO ASSEMBLY MODE
            error_view.display = False
            asm_view.display = True
            title.update(" ASSEMBLY OUTPUT ")
            title.set_class(True, "panel-title")
            title.set_class(False, "error-title")
            
            # Use Member D's Highlighting Logic
            asm_lines = state.asm_content.splitlines()
            # Convert state.perf_stats {asm_idx: stats} to {line_num: latency}
            # Note: asm_idx is 0-based, build_gutter expects 1-based line_num
            cycle_counts = {idx + 1: s.latency for idx, s in state.perf_stats.items()}
            
            rendered_asm = build_gutter(asm_lines, cycle_counts)
            asm_view.update(rendered_asm)

    def action_refresh(self) -> None:
        self.engine.refresh()

    def on_unmount(self) -> None:
        self.engine.stop()

def run_tui(source_file: str):
    app = LocalBoltApp(source_file)
    app.run()
