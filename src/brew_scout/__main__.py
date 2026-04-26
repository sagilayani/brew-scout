"""Entry point for brew-scout."""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="brew-scout",
        description="Discover non-Homebrew apps and onboard them",
    )
    parser.add_argument(
        "--app",
        help="Onboard a specific app by name (e.g. 'Arc', 'Slack')",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="onboard_all",
        help="Onboard all matched apps without prompting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be onboarded without actually doing it",
    )
    args = parser.parse_args()

    if args.app or args.onboard_all or args.dry_run:
        _run_cli(app_name=args.app, onboard_all=args.onboard_all, dry_run=args.dry_run)
    else:
        from brew_scout.app import BrewScoutApp
        app = BrewScoutApp()
        app.run()


def _run_cli(app_name: str | None, onboard_all: bool, dry_run: bool) -> None:
    from rich.console import Console
    from rich.table import Table

    from brew_scout.cask_cache import CaskCache
    from brew_scout.matcher import match_all
    from brew_scout.onboarder import adopt_cask
    from brew_scout.scanner import scan_applications

    console = Console()

    console.print("[bold]Scanning applications...[/]")
    apps = scan_applications()

    console.print("[bold]Loading cask database...[/]")
    cache = CaskCache.load()

    matches = match_all(apps, cache)
    matched = [m for m in matches if m.cask_token]

    if app_name:
        # Filter to specific app
        target = app_name.lower()
        matched = [
            m for m in matched
            if target in m.app.name.lower() or target in (m.cask_token or "")
        ]
        if not matched:
            console.print(f"[red]No match found for '{app_name}'[/]")
            console.print("[dim]Tip: run brew-scout without --app to see all matches[/]")
            sys.exit(1)

    if not matched:
        console.print("[yellow]No apps to onboard.[/]")
        return

    # Show what we found
    table = Table(title="Apps to Onboard")
    table.add_column("App", style="bold")
    table.add_column("Cask")
    table.add_column("Confidence")
    table.add_column("Method")
    table.add_column("Installed Ver")
    table.add_column("Cask Ver")

    for m in sorted(matched, key=lambda m: (-m.confidence, m.app.name.lower())):
        table.add_row(
            m.app.name,
            m.cask_token,
            f"{m.confidence:.0%}",
            m.match_method,
            m.app.version,
            m.cask_version or "?",
        )
    console.print(table)

    if dry_run:
        console.print(f"\n[dim]Dry run: {len(matched)} app(s) would be onboarded[/]")
        return

    if not onboard_all and not app_name:
        return

    # Do the onboarding
    console.print(f"\n[bold]Onboarding {len(matched)} app(s)...[/]\n")
    succeeded = 0
    failed = 0
    for m in matched:
        console.print(f"[cyan]brew install --cask --adopt {m.cask_token}[/]")
        result = adopt_cask(m.cask_token, app_path=m.app.path, on_line=lambda line: console.print(f"  {line}"))
        if result.success:
            console.print(f"  [green]Done[/]\n")
            succeeded += 1
        else:
            console.print(f"  [red]Failed[/]\n")
            failed += 1

    console.print(f"\n[bold]Summary:[/] {succeeded} succeeded, {failed} failed")


if __name__ == "__main__":
    main()
