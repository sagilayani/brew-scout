"""Entry point for brew-scout."""

from brew_scout.app import BrewScoutApp


def main() -> None:
    app = BrewScoutApp()
    app.run()


if __name__ == "__main__":
    main()
