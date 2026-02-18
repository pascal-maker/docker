"""Imports and calls greet from greeter. Run rename_symbol here when renaming greet."""

from __future__ import annotations

from playground.greeter import greet


def main() -> None:
    """Print greeting for a fixed name."""
    print(greet("World"))


if __name__ == "__main__":
    main()
