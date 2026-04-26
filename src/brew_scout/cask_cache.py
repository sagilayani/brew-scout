"""Fetch and cache the Homebrew cask API for fast lookups."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

CASK_API_URL = "https://formulae.brew.sh/api/cask.json"
CACHE_DIR = Path.home() / ".cache" / "brew-scout"
CACHE_FILE = CACHE_DIR / "cask.json"
CACHE_TTL_SECONDS = 86400  # 24 hours


@dataclass
class CaskCache:
    app_name_to_token: dict[str, str] = field(default_factory=dict)
    bundle_id_to_token: dict[str, str] = field(default_factory=dict)
    normalized_name_to_token: dict[str, str] = field(default_factory=dict)
    token_to_version: dict[str, str] = field(default_factory=dict)
    all_tokens: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> CaskCache:
        raw = cls._get_raw_data()
        cache = cls()
        cache._build_lookups(raw)
        return cache

    @classmethod
    def _get_raw_data(cls) -> list[dict]:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        if CACHE_FILE.exists():
            age = time.time() - CACHE_FILE.stat().st_mtime
            if age < CACHE_TTL_SECONDS:
                return json.loads(CACHE_FILE.read_text())

        req = urllib.request.Request(CASK_API_URL, headers={"User-Agent": "brew-scout/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        CACHE_FILE.write_text(json.dumps(data))
        return data

    def _build_lookups(self, casks: list[dict]) -> None:
        for cask in casks:
            token = cask.get("token", "")
            if not token:
                continue

            self.all_tokens.append(token)
            self.token_to_version[token] = cask.get("version", "")

            is_base = "@" not in token  # base tokens preferred over variants

            # Normalized name lookup: token itself + display names
            if is_base or token not in self.normalized_name_to_token:
                self.normalized_name_to_token[token] = token
            for name in cask.get("name", []):
                normalized = name.lower().replace(" ", "-")
                if is_base or normalized not in self.normalized_name_to_token:
                    self.normalized_name_to_token[normalized] = token

            # App artifact lookup: e.g., "Slack.app" -> "slack"
            for artifact in cask.get("artifacts", []):
                if isinstance(artifact, dict):
                    for app_entry in artifact.get("app", []):
                        if isinstance(app_entry, str):
                            if is_base or app_entry not in self.app_name_to_token:
                                self.app_name_to_token[app_entry] = token
                    # Bundle ID from uninstall quit
                    for uninstall in artifact.get("uninstall", []):
                        if isinstance(uninstall, dict):
                            for quit_id in uninstall.get("quit", []):
                                if isinstance(quit_id, str):
                                    if is_base or quit_id not in self.bundle_id_to_token:
                                        self.bundle_id_to_token[quit_id] = token
                    for zap in artifact.get("zap", []):
                        if isinstance(zap, dict):
                            for quit_id in zap.get("quit", []):
                                if isinstance(quit_id, str):
                                    self.bundle_id_to_token.setdefault(quit_id, token)
