"""Main Textual application for brew-scout."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from brew_scout.screens.scan import ScanScreen

APP_CSS = """
Screen {
    background: $surface;
}

#title {
    text-align: center;
    text-style: bold;
    margin: 1 0;
}

#scan-status {
    text-align: center;
    margin: 1 0;
    color: $text-muted;
}

#match-list {
    height: 1fr;
    margin: 1 2;
    border: round $primary;
}

#apply-bar {
    height: auto;
    margin: 1 2;
    padding: 1;
    layout: horizontal;
}

#apply-bar Button {
    margin: 0 1;
}

#summary {
    margin: 0 2;
    height: auto;
}

#progress {
    margin: 1 2;
}

#progress-label {
    margin: 0 2;
    height: auto;
}

#install-log {
    height: 1fr;
    margin: 1 2;
    border: round $accent;
    background: $surface-darken-2;
}

#btn-done {
    margin: 1 2;
}
"""


class BrewScoutApp(App):
    CSS = APP_CSS
    TITLE = "brew-scout"
    SUB_TITLE = "Discover & Onboard Non-Homebrew Apps"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(ScanScreen())


def main() -> None:
    app = BrewScoutApp()
    app.run()
