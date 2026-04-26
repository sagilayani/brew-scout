"""Run brew install --cask --adopt for selected apps."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable

from brew_scout.models import OnboardResult

BREW_BIN = shutil.which("brew") or "/opt/homebrew/bin/brew"


def adopt_cask(
    token: str,
    on_line: Callable[[str], None] | None = None,
) -> OnboardResult:
    proc = subprocess.Popen(
        [BREW_BIN, "install", "--cask", "--adopt", token],
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
    output = "\n".join(lines)
    return OnboardResult(
        cask_token=token,
        success=proc.returncode == 0,
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
