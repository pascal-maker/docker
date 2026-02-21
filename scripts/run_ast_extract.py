"""Run AST refactor agent to extract a block into a new function.

Uses testdata/sample_for_extract.py: extracts the print(x + y) line
into a function named print_sum(x, y), then prints before/after.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from refactor_agent.agent.runner import run_ast_extract_function

TEST_FILE = Path(__file__).resolve().parent / "testdata" / "sample_for_extract.py"


def main() -> None:
    source = TEST_FILE.read_text()
    # Extract line 6 (print(x + y)) from main() into print_sum
    after = asyncio.run(
        run_ast_extract_function(
            source,
            scope_function="main",
            start_line=6,
            end_line=6,
            new_function_name="print_sum",
        )
    )
    print("Before:")
    print(source)
    print("After:")
    print(after)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()

    from langfuse import get_client

    get_client().flush()
