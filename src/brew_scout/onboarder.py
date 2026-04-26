"""Run brew install --cask --adopt for selected apps."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable

from brew_scout.models import OnboardResult

BREW_BIN = shutil.which("brew") or "/opt/homebrew/bin/brew"


def _run_brew_cask(
    args: list[str],
    on_line: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    proc = subprocess.Popen(
        [BREW_BIN, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines: list[str] = []
    for line in iter(proc.stdout.readline, ""):
        stripped = line.rstrip()
        lines.append(stripped)
        if on_line:
            on_line(stripped)
    proc.wait()
    return proc.returncode, "\n".join(lines)


def adopt_cask(
    token: str,
    on_line: Callable[[str], None] | None = None,
) -> OnboardResult:
    # Try --adopt first (zero-disruption if versions match)
    returncode, output = _run_brew_cask(
        ["install", "--cask", "--adopt", token],
        on_line=on_line,
    )

    if returncode != 0 and "different from the one being installed" in output:
        if on_line:
            on_line("")
            on_line("Version mismatch — your app is outdated.")
            on_line(f"Update {token} through the app itself, then retry brew-scout.")
            on_line("")

    return OnboardResult(
        cask_token=token,
        success=returncode == 0,
        output=output,
    )


def adopt_multiple(
    tokens: list[str],
    on_line: Callable[[str], None] | None = None,
    on_complete: Callable[[OnboardResult], None] | None = None,
) -> list[OnboardResult]:
    results: list[OnboardResult] = []
    for token in tokens:
        if on_line:
            on_line(f"\n{'='*40}")
            on_line(f"Installing {token}...")
            on_line(f"{'='*40}")
        result = adopt_cask(token, on_line=on_line)
        results.append(result)
        if on_complete:
            on_complete(result)
    return results
