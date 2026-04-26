"""Match scanned apps to Homebrew cask tokens using a 4-tier strategy."""

from __future__ import annotations

import difflib
from pathlib import Path

from brew_scout.cask_cache import CaskCache
from brew_scout.models import AppInfo, CaskMatch


def match_app(app: AppInfo, cache: CaskCache) -> CaskMatch:
    # Tier 1: Exact app artifact match (e.g., "Slack.app" -> "slack")
    app_filename = Path(app.path).name  # "Slack.app"
    if app_filename in cache.app_name_to_token:
        token = cache.app_name_to_token[app_filename]
        return CaskMatch(
            app=app,
            cask_token=token,
            cask_version=cache.token_to_version.get(token),
            confidence=1.0,
            match_method="exact-app",
        )

    # Tier 2: Exact bundle ID match
    if app.bundle_id and app.bundle_id in cache.bundle_id_to_token:
        token = cache.bundle_id_to_token[app.bundle_id]
        return CaskMatch(
            app=app,
            cask_token=token,
            cask_version=cache.token_to_version.get(token),
            confidence=1.0,
            match_method="exact-bundle-id",
        )

    # Tier 3: Normalized name lookup
    stem = Path(app.path).stem  # "Google Chrome"
    normalized = stem.lower().replace(" ", "-")
    if normalized in cache.normalized_name_to_token:
        token = cache.normalized_name_to_token[normalized]
        return CaskMatch(
            app=app,
            cask_token=token,
            cask_version=cache.token_to_version.get(token),
            confidence=0.9,
            match_method="normalized-name",
        )

    # Tier 3b: Try display name (CFBundleName) normalized
    display_normalized = app.name.lower().replace(" ", "-")
    if display_normalized != normalized and display_normalized in cache.normalized_name_to_token:
        token = cache.normalized_name_to_token[display_normalized]
        return CaskMatch(
            app=app,
            cask_token=token,
            cask_version=cache.token_to_version.get(token),
            confidence=0.9,
            match_method="normalized-name",
        )

    # Tier 4: Fuzzy match against all tokens (high cutoff to avoid false positives)
    # Try both the .app stem and the display name
    candidates = {normalized, display_normalized}
    best_token: str | None = None
    best_ratio = 0.0
    for candidate in candidates:
        matches = difflib.get_close_matches(candidate, cache.all_tokens, n=1, cutoff=0.9)
        if matches:
            token = matches[0]
            ratio = difflib.SequenceMatcher(None, candidate, token).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_token = token

    if best_token:
        return CaskMatch(
            app=app,
            cask_token=best_token,
            cask_version=cache.token_to_version.get(best_token),
            confidence=round(best_ratio, 2),
            match_method="fuzzy",
        )

    # No match
    return CaskMatch(
        app=app,
        cask_token=None,
        cask_version=None,
        confidence=0.0,
        match_method="none",
    )


def match_all(apps: list[AppInfo], cache: CaskCache) -> list[CaskMatch]:
    unmanaged = [a for a in apps if not a.is_brew_managed]
    return [match_app(app, cache) for app in unmanaged]
