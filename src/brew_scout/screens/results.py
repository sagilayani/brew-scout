"""Results screen — show matched apps with selection checkboxes."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, SelectionList, Static
from textual.widgets.selection_list import Selection

from brew_scout.models import CaskMatch


class ResultsScreen(Screen):
    BINDINGS = [
        ("a", "select_all", "Select All"),
        ("n", "select_none", "Deselect All"),
        ("enter", "onboard", "Onboard Selected"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, matches: list[CaskMatch]) -> None:
        super().__init__()
        self._matches = matches

    def compose(self) -> ComposeResult:
        matched = [m for m in self._matches if m.cask_token]
        unmatched = [m for m in self._matches if not m.cask_token]

        yield Label(f"Found {len(matched)} matchable apps, {len(unmatched)} unmatched")
        yield Static(id="summary")
        yield SelectionList[str](id="match-list")
        with Horizontal(id="apply-bar"):
            yield Button("Onboard Selected", id="btn-onboard", variant="success")
            yield Button("Onboard All", id="btn-onboard-all", variant="warning")
            yield Button("Select All", id="btn-all", variant="default")
            yield Button("Deselect All", id="btn-none", variant="default")
            yield Button("Quit", id="btn-quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        sel_list = self.query_one("#match-list", SelectionList)

        matched = sorted(
            [m for m in self._matches if m.cask_token],
            key=lambda m: (-m.confidence, m.app.name.lower()),
        )

        for m in matched:
            confidence_pct = f"{m.confidence:.0%}"
            label = (
                f"{m.app.name} → {m.cask_token}  "
                f"[{confidence_pct}, {m.match_method}]  "
                f"(installed: {m.app.version}, cask: {m.cask_version or '?'})"
            )
            sel_list.add_option(Selection(label, m.cask_token, False))

        # Show unmatched summary
        unmatched = [m for m in self._matches if not m.cask_token]
        if unmatched:
            names = ", ".join(m.app.name for m in unmatched[:10])
            extra = f" (+{len(unmatched) - 10} more)" if len(unmatched) > 10 else ""
            self.query_one("#summary", Static).update(
                f"[dim]Unmatched: {names}{extra}[/]"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        sel_list = self.query_one("#match-list", SelectionList)
        if event.button.id == "btn-all":
            sel_list.select_all()
        elif event.button.id == "btn-none":
            sel_list.deselect_all()
        elif event.button.id == "btn-onboard":
            self._start_onboard()
        elif event.button.id == "btn-onboard-all":
            sel_list.select_all()
            self._start_onboard()
        elif event.button.id == "btn-quit":
            self.app.exit()

    def action_select_all(self) -> None:
        self.query_one("#match-list", SelectionList).select_all()

    def action_select_none(self) -> None:
        self.query_one("#match-list", SelectionList).deselect_all()

    def action_onboard(self) -> None:
        self._start_onboard()

    def _start_onboard(self) -> None:
        sel_list = self.query_one("#match-list", SelectionList)
        selected = list(sel_list.selected)
        if not selected:
            self.notify("No packages selected", severity="warning")
            return
        from brew_scout.screens.onboard import OnboardScreen
        self.app.switch_screen(OnboardScreen(selected))

    def action_quit(self) -> None:
        self.app.exit()
