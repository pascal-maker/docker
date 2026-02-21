"""Another consumer of greet(). Run rename_symbol here as well for cross-file rename."""

from __future__ import annotations

from playground.python.greeter import greet_user


def main() -> None:
    """Print two greetings."""
    print(greet_user("Alice"))
    print(greet_user("Bob"))


if __name__ == "__main__":
    main()
