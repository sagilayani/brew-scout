"""Scan screen — show progress while scanning /Applications."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, LoadingIndicator, Static

from brew_scout.cask_cache import CaskCache
from brew_scout.matcher import match_all
from brew_scout.models import CaskMatch
from brew_scout.scanner import scan_applications


class ScanScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("brew-scout", id="title")
        yield LoadingIndicator()
        yield Static("Scanning /Applications and loading cask database...", id="scan-status")

    def on_mount(self) -> None:
        self.run_worker(self._do_scan, thread=True)

    def _do_scan(self) -> None:
        self.app.call_from_thread(self._set_status, "Scanning installed applications...")
        apps = scan_applications()
        self.app.call_from_thread(self._set_status, f"Found {len(apps)} apps. Loading cask database...")

        cache = CaskCache.load()
        self.app.call_from_thread(self._set_status, f"Matching {len(apps)} apps against {len(cache.all_tokens)} casks...")

        matches = match_all(apps, cache)
        self.app.call_from_thread(self._scan_complete, matches)

    def _set_status(self, text: str) -> None:
        self.query_one("#scan-status", Static).update(text)

    def _scan_complete(self, matches: list[CaskMatch]) -> None:
        from brew_scout.screens.results import ResultsScreen
        self.app.switch_screen(ResultsScreen(matches))
