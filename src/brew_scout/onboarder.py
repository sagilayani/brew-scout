"""Run brew install --cask --adopt for selected apps."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

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
    app_path: str | None = None,
    on_line: Callable[[str], None] | None = None,
) -> OnboardResult:
    # Try --adopt first (zero-disruption if versions match)
    returncode, output = _run_brew_cask(
        ["install", "--cask", "--adopt", token],
        on_line=on_line,
    )

    if returncode != 0 and "different from the one being installed" in output:
        if not app_path:
            # No app path — can't do the move-aside fallback
            if on_line:
                on_line("")
                on_line("Version mismatch and app path unknown — skipping.")
            return OnboardResult(cask_token=token, success=False, output=output)

        # Move existing app aside, clean install, remove old copy
        app = Path(app_path)
        backup = app.with_suffix(".app.bak")

        if on_line:
            on_line("")
            on_line(f"Version mismatch — moving {app.name} aside and installing via brew...")

        app.rename(backup)
        try:
            returncode, install_output = _run_brew_cask(
                ["install", "--cask", token],
                on_line=on_line,
            )
            output = output + "\n" + install_output

            if returncode == 0:
                # Clean install succeeded — remove old backup
                if backup.exists():
                    shutil.rmtree(backup)
                if on_line:
                    on_line(f"Done — {token} is now managed by brew.")
            else:
                # Install failed — restore the original app
                if backup.exists():
                    if app.exists():
                        shutil.rmtree(app)
                    backup.rename(app)
                if on_line:
                    on_line("Install failed — restored original app.")
        except Exception as e:
            # Something went wrong — restore
            if backup.exists() and not app.exists():
                backup.rename(app)
            if on_line:
                on_line(f"Error: {e} — restored original app.")
            returncode = 1

    return OnboardResult(
        cask_token=token,
        success=returncode == 0,
        output=output,
    )


def adopt_multiple(
    tokens_with_paths: list[tuple[str, str | None]],
    on_line: Callable[[str], None] | None = None,
    on_complete: Callable[[OnboardResult], None] | None = None,
) -> list[OnboardResult]:
    results: list[OnboardResult] = []
    for token, app_path in tokens_with_paths:
        if on_line:
            on_line(f"\n{'='*40}")
            on_line(f"Installing {token}...")
            on_line(f"{'='*40}")
        result = adopt_cask(token, app_path=app_path, on_line=on_line)
        results.append(result)
        if on_complete:
            on_complete(result)
    return results
