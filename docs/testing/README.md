# Testing the refactor schedule flow

This doc describes how to manually (and optionally automatically) verify the planning pipeline: **prompt → plan → execute → check results**, using the DDD playgrounds and the Dev UI.

## Purpose

- **Manual:** Confirm that multi-step refactor requests produce a `RefactorSchedule`, that Plan mode shows it only, and that Auto/Ask execute it and leave the workspace in the expected shape.
- **Automation:** Unit tests cover models, executor validation (cycles, unknown deps), and parsing; integration tests can run the executor against a fixture schedule and assert on file layout.

## Playgrounds as fixtures

The [Python](../../playground/python/README.md) and [TypeScript](../../playground/typescript/README.md) playgrounds are laid out in **Domain Driven Design** style with **intentional boundary violations** (e.g. a backend use case under `frontend/`). They are the standard target for “multi-step refactor” tests. See the playground READMEs for layout and example prompts.

## How to test manually

1. **Start from a known state**  
   Reset the playground if needed (e.g. `git checkout playground/`) so you have the original DDD layout and violations.

2. **Open the Dev UI**  
   Run `make ui`, choose the workspace language (Python or TypeScript), and note the **mode** (Ask | Edit=Auto | Plan).

3. **Plan mode**  
   Use a prompt that requires multiple operations, for example:
   - “Refactor this codebase to a vertical slice structure.”
   - “Enforce frontend/backend boundary: move backend use cases out of the frontend folder.”
   - “Create a plan to reorganize the project so the frontend layer does not contain domain logic.”

   Confirm that the agent returns a **RefactorSchedule** (displayed in the UI) with several operations (e.g. `move_symbol`, `organize_imports`). In Plan mode, execution should not run; you should see a note that you can switch to Auto or Ask to execute.

4. **Auto or Ask mode**  
   Run the same (or a new) conversation with the same or similar prompt. In **Auto** the schedule should execute immediately after the agent produces it. In **Ask** you should see the schedule and a “Proceed with execution?” prompt; reply “yes” to run. Then verify:
   - Directory and file layout match the target structure.
   - Imports are correct and there are no broken references (e.g. run the project or a quick lint if available).

5. **Reset and repeat**  
   Optionally reset the playground (`git checkout playground/`) and try another prompt or target pattern.

## Checking results

- **Layout:** Inspect `playground/python/` or `playground/typescript/src/` and confirm moved/renamed files and folders match the plan.
- **Symbols:** Search for moved symbol names (e.g. `get_order_handler`) to ensure they appear only where expected.
- **Run the playground:** From repo root, e.g. `uv run python -c "from playground.python.application.use_cases.create_order import create_order; ..."` or build/run the TypeScript playground to ensure nothing is broken.

## Automation

- **Unit tests** in `tests/test_schedule/`:
  - `test_models.py`: `RefactorSchedule` and operation variants parse from the JSON fixture and round-trip.
  - `test_executor.py`: Executor rejects cycles in `dependsOn`, unknown dependency ids, and non-TypeScript workspaces in PoC.
- **Integration:** You can add tests that load a `RefactorSchedule` fixture, run `execute_schedule()` against a copy of the playground (e.g. `tmp_path` with copied files), and assert on expected file contents or structure. See [refactor-schedule README](refactor-schedule/README.md) for the data model and executor contract.

## Links

- [Refactor schedule (data model, pipeline)](../refactor-schedule/README.md)
- [Chat UI (modes, single vs multi-step)](../chat-ui.md)
- [Python playground README](../playground/python/README.md)
- [TypeScript playground README](../playground/typescript/README.md)
