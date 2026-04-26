"""Data models for brew-scout."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppInfo:
    name: str
    path: str
    bundle_id: str
    version: str
    is_brew_managed: bool


@dataclass(frozen=True)
class CaskMatch:
    app: AppInfo
    cask_token: str | None
    cask_version: str | None
    confidence: float
    match_method: str


@dataclass(frozen=True)
class OnboardResult:
    cask_token: str
    success: bool
    output: str
