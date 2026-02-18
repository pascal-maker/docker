"""Run AST refactor agent on hardcoded test file (calculate_tax -> compute_tax)."""

from __future__ import annotations

import asyncio

from document_structuring_agent.ast_refactor import run_ast_refactor

_TEST_SOURCE = """def calculate_tax(amount, rate):
    return round(amount * rate, 2)

def calculate_total(price, quantity, tax_rate):
    subtotal = price * quantity
    tax = calculate_tax(subtotal, tax_rate)
    return subtotal + tax

def main():
    total = calculate_total(10.0, 3, 0.2)
    print(f"Total: {total}")

if __name__ == "__main__":
    main()
"""


def main() -> None:
    after = asyncio.run(run_ast_refactor(_TEST_SOURCE, "calculate_tax", "compute_tax"))
    print("Before:")
    print(_TEST_SOURCE)
    print("After:")
    print(after)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()

    from langfuse import get_client

    get_client().flush()
