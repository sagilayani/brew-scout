"""Run brew install --cask --adopt for selected apps."""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from brew_scout.models import OnboardResult

BREW_BIN = shutil.which("brew") or "/opt/homebrew/bin/brew"
CASKROOM = Path("/opt/homebrew/Caskroom")


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


def _get_installed_version(app_path: str) -> str:
    """Read the app's actual version from its Info.plist."""
    plist_path = Path(app_path) / "Contents" / "Info.plist"
    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)
    return plist.get("CFBundleShortVersionString", plist.get("CFBundleVersion", "unknown"))


def _get_cask_json(token: str) -> dict | None:
    """Get cask metadata from brew info."""
    result = subprocess.run(
        [BREW_BIN, "info", "--cask", "--json=v2", token],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return None
    data = json.loads(result.stdout)
    casks = data.get("casks", [])
    return casks[0] if casks else None


def _register_cask(token: str, app_path: str, on_line: Callable[[str], None] | None = None) -> bool:
    """Register an existing app with brew by creating Caskroom metadata."""
    installed_version = _get_installed_version(app_path)
    cask_info = _get_cask_json(token)
    if not cask_info:
        if on_line:
            on_line(f"Could not fetch cask info for {token}")
        return False

    app = Path(app_path)
    app_filename = app.name  # e.g. "AnyDesk.app"

    if on_line:
        on_line(f"Registering {app_filename} (v{installed_version}) with brew...")

    # Create Caskroom version directory with symlink
    version_dir = CASKROOM / token / installed_version
    version_dir.mkdir(parents=True, exist_ok=True)
    symlink = version_dir / app_filename
    if not symlink.exists():
        symlink.symlink_to(app_path)

    # Create .metadata directory
    timestamp = time.strftime("%Y%m%d%H%M%S.000")
    meta_dir = CASKROOM / token / ".metadata"
    meta_version_dir = meta_dir / installed_version / timestamp / "Casks"
    meta_version_dir.mkdir(parents=True, exist_ok=True)

    # Write cask JSON (with version overridden to installed version)
    cask_json = dict(cask_info)
    cask_json["version"] = installed_version
    cask_json["installed"] = installed_version
    cask_json["installed_time"] = int(time.time())
    cask_json_path = meta_version_dir / f"{token}.json"
    cask_json_path.write_text(json.dumps(cask_json, indent=2))

    # Write INSTALL_RECEIPT.json
    receipt = {
        "homebrew_version": subprocess.run(
            [BREW_BIN, "--version"], capture_output=True, text=True
        ).stdout.strip().split("\n")[0].replace("Homebrew ", ""),
        "loaded_from_api": True,
        "uninstall_flight_blocks": False,
        "installed_as_dependency": False,
        "installed_on_request": True,
        "time": int(time.time()),
        "runtime_dependencies": {},
        "source": {
            "tap": "homebrew/cask",
            "tap_git_head": "",
            "version": installed_version,
            "path": "",
        },
        "arch": os.uname().machine,
        "uninstall_artifacts": [a for a in cask_info.get("artifacts", []) if isinstance(a, dict)],
    }
    (meta_dir / "INSTALL_RECEIPT.json").write_text(json.dumps(receipt, indent=2))

    # Write config.json
    config = {
        "default": {
            "appdir": "/Applications",
        },
        "env": {},
        "explicit": {},
    }
    (meta_dir / "config.json").write_text(json.dumps(config))

    if on_line:
        on_line(f"Registered {token} v{installed_version} with brew.")
        on_line(f"Run 'brew upgrade --cask {token}' later to update to latest.")

    return True


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
            if on_line:
                on_line("")
                on_line("Version mismatch and app path unknown — skipping.")
            return OnboardResult(cask_token=token, success=False, output=output)

        # Version mismatch — register the app at its current version
        if on_line:
            on_line("")
            on_line("Version mismatch — registering existing version with brew...")

        # Clean up the failed --adopt attempt's Caskroom entry
        failed_dir = CASKROOM / token
        if failed_dir.exists():
            shutil.rmtree(failed_dir)

        success = _register_cask(token, app_path, on_line=on_line)
        returncode = 0 if success else 1

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
