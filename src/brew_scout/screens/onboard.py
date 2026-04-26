"""Onboard screen — install selected casks with --adopt and show progress."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, ProgressBar, RichLog

from brew_scout.models import OnboardResult
from brew_scout.onboarder import adopt_multiple


class OnboardScreen(Screen):
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, tokens_with_paths: list[tuple[str, str | None]]) -> None:
        super().__init__()
        self._tokens_with_paths = tokens_with_paths
        self._results: list[OnboardResult] = []
        self._completed = 0

    def compose(self) -> ComposeResult:
        yield Label(f"Onboarding {len(self._tokens_with_paths)} packages via brew install --cask --adopt")
        yield ProgressBar(id="progress", total=len(self._tokens_with_paths), show_eta=True)
        yield Label(id="progress-label")
        yield RichLog(id="install-log", highlight=True, markup=True, wrap=True)
        yield Button("Done", id="btn-done", variant="success", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._do_onboard, thread=True)

    def _do_onboard(self) -> None:
        def on_line(line: str) -> None:
            highlighted = line
            if "error" in line.lower():
                highlighted = f"[bold red]{line}[/]"
            elif "warning" in line.lower():
                highlighted = f"[bold yellow]{line}[/]"
            elif line.startswith("==>"):
                highlighted = f"[bold cyan]{line}[/]"
            self.app.call_from_thread(
                self.query_one("#install-log", RichLog).write,
                highlighted,
            )

        def on_complete(result: OnboardResult) -> None:
            self._completed += 1
            self._results.append(result)
            status = "[green]OK[/]" if result.success else "[red]FAILED[/]"
            self.app.call_from_thread(self._update_progress, result.cask_token, status)

        self._results = adopt_multiple(
            self._tokens_with_paths,
            on_line=on_line,
            on_complete=on_complete,
        )
        self.app.call_from_thread(self._install_done)

    def _update_progress(self, token: str, status: str) -> None:
        self.query_one("#progress", ProgressBar).advance(1)
        self.query_one("#progress-label", Label).update(
            f"{self._completed}/{len(self._tokens_with_paths)}: {token} {status}"
        )

    def _install_done(self) -> None:
        log = self.query_one("#install-log", RichLog)
        log.write("")
        log.write("[bold]" + "=" * 50 + "[/]")
        log.write("[bold]Summary[/]")
        log.write("[bold]" + "=" * 50 + "[/]")

        succeeded = [r for r in self._results if r.success]
        failed = [r for r in self._results if not r.success]

        log.write(f"\n[green]Succeeded: {len(succeeded)}[/]")
        for r in succeeded:
            log.write(f"  [green]✓[/] {r.cask_token}")

        if failed:
            log.write(f"\n[red]Failed: {len(failed)}[/]")
            for r in failed:
                log.write(f"  [red]✗[/] {r.cask_token}")

        self.query_one("#btn-done", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-done":
            self.app.exit()

    def action_quit(self) -> None:
        self.app.exit()
