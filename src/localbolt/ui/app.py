from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea, DataTable
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from ..engine import BoltEngine
from ..utils.state import LocalBoltState

class LocalBoltApp(App):
    """LocalBolt: Focused Assembly Explorer."""

    CSS = """
    Screen {
        background: #1e1e1e;
    }
    #asm-container {
        width: 70%;
        border-right: heavy $primary;
    }
    #perf-container {
        width: 30%;
    }
    .panel-title {
        background: $primary;
        color: white;
        text-align: center;
        width: 100%;
        padding: 0 1;
    }
    TextArea {
        border: none;
    }
    DataTable {
        height: 100%;
    }
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
        yield Horizontal(
            Vertical(
                Static(" ASSEMBLY OUTPUT ", classes="panel-title"),
                TextArea(id="asm-view", language="asm", read_only=True),
                id="asm-container"
            ),
            Vertical(
                Static(" PERFORMANCE (llvm-mca) ", classes="panel-title"),
                DataTable(id="perf-table"),
                id="perf-container"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#perf-table", DataTable)
        table.add_columns("Line", "Instr", "Cycles")
        table.cursor_type = "row"
        
        self.engine.start()
        self.notify(f"Monitoring {self.engine.state.source_path}")

    def on_local_bolt_app_state_updated(self, message: StateUpdated) -> None:
        state = message.state
        asm_view = self.query_one("#asm-view", TextArea)
        perf_table = self.query_one("#perf-table", DataTable)
        
        # 1. Update Assembly
        asm_view.text = state.asm_content
        
        # 2. Update Perf Table
        perf_table.clear()
        # llvm-mca indices might not align perfectly with cleaned ASM indices
        # For now, we show the raw instruction stats we parsed
        for idx, stats in state.perf_stats.items():
            perf_table.add_row(
                str(idx),
                "instr", # We could extract the mnemonic here if needed
                f"{stats.latency}c"
            )
        
        if state.compiler_output and "warning" in state.compiler_output.lower():
            self.notify("Recompiled with warnings", severity="warning")
        elif state.compiler_output:
             self.notify("Compilation error", severity="error")
        else:
            self.notify("Updated")

    def action_refresh(self) -> None:
        self.engine.refresh()

    def on_unmount(self) -> None:
        self.engine.stop()

def run_tui(source_file: str):
    app = LocalBoltApp(source_file)
    app.run()
