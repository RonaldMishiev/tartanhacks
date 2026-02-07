from textual.widgets import Static, Input
from textual.message import Message
from textual.containers import Center, Middle
from textual.binding import Binding

class FlagsPopup(Static):
    """A centered command palette for entering compiler flags."""
    
    DEFAULT_CSS = """
    FlagsPopup {
        display: none;
        width: 60;
        height: auto;
        background: #EBEEEE;
        border: solid #45d3ee;
        padding: 1 2;
        align: center middle;
    }

    FlagsPopup .title {
        color: #191A1A;
        text-style: bold;
        margin-bottom: 1;
    }

    FlagsPopup Input {
        background: #FFFFFF;
        color: #191A1A;
        border: solid #94bfc1;
    }
    """

    class FlagsChanged(Message):
        def __init__(self, flags: str) -> None:
            super().__init__()
            self.flags = flags

    def compose(self):
        yield Static("Compiler Flags", classes="title")
        yield Input(placeholder="-O3 -mavx2 ...", id="flags-input")

    def on_input_submitted(self, event: Input.Submitted):
        self.post_message(self.FlagsChanged(event.value))
        self.display = False

    def on_key(self, event):
        if event.key == "escape":
            self.display = False

    def show(self, current_flags: str):
        self.display = True
        input_widget = self.query_one("#flags-input", Input)
        input_widget.value = current_flags
        input_widget.focus()
