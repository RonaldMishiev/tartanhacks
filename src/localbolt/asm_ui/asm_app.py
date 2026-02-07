from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import VerticalScroll
from textual.binding import Binding

try:
    from ..utils.highlighter import build_gutter
except ImportError:
    # Run as script (e.g. python asm_app.py): add package root to path
    import sys
    _src = Path(__file__).resolve().parents[2]
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
    from localbolt.utils.highlighter import build_gutter

DEFAULT_ASM = Path(__file__).parent / "test_assembly.txt"


class AsmApp(App):
    """Minimal Textual UI for viewing syntax-highlighted assembly."""

    CSS = """
    Screen { background: #1e1e1e; }
    #asm-scroll { height: 1fr; }
    #asm-view { width: auto; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, asm_file: str | Path = DEFAULT_ASM, cycle_counts: dict[int, int] | None = None):
        super().__init__()
        self.asm_file = Path(asm_file)
        self.cycle_counts = cycle_counts or {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static(id="asm-view"), id="asm-scroll")
        yield Footer()

    def on_mount(self) -> None:
        self._load_asm()

    def _load_asm(self) -> None:
        """Read assembly file and display highlighted Rich Text in the panel."""
        lines = self.asm_file.read_text().splitlines()
        rendered = build_gutter(lines, self.cycle_counts)
        self.query_one("#asm-view", Static).update(rendered)

    def action_refresh(self) -> None:
        self._load_asm()


def run_asm_app(asm_file: str | Path = DEFAULT_ASM, cycle_counts: dict[int, int] | None = None):
    AsmApp(asm_file, cycle_counts).run()


if __name__ == "__main__":
    sample_cycles = {1: 1, 2: 1, 3: 3, 4: 1, 5: 1, 6: 2, 7: 6, 8: 1, 9: 1}
    run_asm_app(cycle_counts=sample_cycles)
