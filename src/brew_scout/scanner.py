"""Scan /Applications for installed apps and read their metadata."""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

from brew_scout.models import AppInfo

SCAN_DIRS = [
    Path("/Applications"),
    Path.home() / "Applications",
]

BREW_BIN = shutil.which("brew") or "/opt/homebrew/bin/brew"


def get_brew_managed_casks() -> set[str]:
    result = subprocess.run(
        [BREW_BIN, "list", "--cask", "-1"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {line.strip() for line in result.stdout.strip().splitlines() if line.strip()}


def scan_applications() -> list[AppInfo]:
    managed = get_brew_managed_casks()
    apps: list[AppInfo] = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for entry in scan_dir.iterdir():
            if not entry.name.endswith(".app"):
                continue
            info_plist = entry / "Contents" / "Info.plist"
            if not info_plist.exists():
                continue

            try:
                with open(info_plist, "rb") as f:
                    plist = plistlib.load(f)
            except Exception:
                continue

            name = plist.get("CFBundleName", entry.stem)
            bundle_id = plist.get("CFBundleIdentifier", "")
            version = plist.get("CFBundleShortVersionString", plist.get("CFBundleVersion", "unknown"))

            # Check if managed by brew: normalize app name to cask-like token
            normalized = entry.stem.lower().replace(" ", "-")
            is_managed = normalized in managed

            apps.append(AppInfo(
                name=name,
                path=str(entry),
                bundle_id=bundle_id,
                version=str(version),
                is_brew_managed=is_managed,
            ))

    return sorted(apps, key=lambda a: a.name.lower())
