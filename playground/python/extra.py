"""Another consumer of greet(). Run rename_symbol here as well for cross-file rename."""

from __future__ import annotations

from playground.python.greeter import greet


def main() -> None:
    """Print two greetings."""
    print(greet("Alice"))
    print(greet("Bob"))


if __name__ == "__main__":
    main()
