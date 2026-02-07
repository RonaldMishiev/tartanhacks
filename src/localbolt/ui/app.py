from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
from ..engine import BoltEngine
from ..utils.state import LocalBoltState
from ..utils.highlighter import build_gutter, INSTRUCTIONS

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
    
    #asm-view {{ width: 200; height: auto; color: {C_TEXT}; }}
    #error-view {{ color: #a80000; display: none; margin: 1 2; }}
    
    .panel-title {{
        color: {C_ACCENT3};
        text-align: center;
        margin-top: 1;
    }}
    
    Footer {{
        background: {C_TEXT};
        color: {C_ACCENT1};
    }}
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
        yield MosaicHeader()
        yield Static(" ASSEMBLY EXPLORER ", id="main-title", classes="panel-title")
        yield Vertical(
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
            title.styles.color = "#a80000"
        else:
            error_view.display = False
            asm_view.display = True
            title.update(" ASSEMBLY EXPLORER ")
            title.styles.color = C_ACCENT3
            
            asm_lines = state.asm_content.splitlines()
            aligned_cycle_counts = {}
            instr_idx = 0
            for line_idx, line in enumerate(asm_lines):
                stripped = line.strip()
                if stripped and not stripped.endswith(":") and INSTRUCTIONS.search(stripped):
                    if instr_idx in state.perf_stats:
                        aligned_cycle_counts[line_idx + 1] = state.perf_stats[instr_idx].latency
                    instr_idx += 1
            
            rendered_asm = build_gutter(asm_lines, aligned_cycle_counts, width=150)
            asm_view.update(rendered_asm)

    def action_refresh(self) -> None:
        self.engine.refresh()

    def on_unmount(self) -> None:
        self.engine.stop()

def run_tui(source_file: str):
    app = LocalBoltApp(source_file)
    app.run()
