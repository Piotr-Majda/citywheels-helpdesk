"""CLI entry point. Run with: python -m app.main."""

import argparse


def main() -> None:
    """Display CLI help until the agent is implemented."""
    parser = argparse.ArgumentParser(description="CityWheels help desk CLI")
    parser.print_help()


if __name__ == "__main__":
    main()
