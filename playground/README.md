# Playground: MCP `rename_symbol` testing

**Purpose:** Minimal fixture for testing the ast-refactor MCP server’s `rename_symbol` tool. Not part of the main app or test suite.

## Files

- **`greeter.py`** – Defines `greet(name)`. This is the canonical definition.
- **`caller.py`** – Imports `greet` from `playground.greeter` and calls it.
- **`extra.py`** – Also imports and calls `greet`.

All three files use the symbol **`greet`**, which you can rename (e.g. to `greet_user`) to verify the MCP tool.

## How to test

1. Open this repo in Cursor with the ast-refactor MCP server configured.
2. Use the MCP **`rename_symbol`** tool once **per file**:
   - In `playground/greeter.py`: rename `greet` → `greet_user` (or another name).
   - In `playground/caller.py`: same rename so the import and call stay consistent.
   - In `playground/extra.py`: same rename.

The tool is **per-file only**: it renames a symbol inside a single Python file (read → LibCST transform → write). To rename across files, run the tool once for each file that defines or uses the symbol.

## Running the playground

From the repo root with `PYTHONPATH` set:

```bash
uv run python -c "from playground.caller import main; main()"
uv run python -c "from playground.extra import main; main()"
```

No extra dependencies; uses only the standard library.
