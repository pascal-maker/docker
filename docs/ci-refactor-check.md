# CI refactor check

The refactor check runs refactor-agent against your repo on each PR (or push): it loads **presets** (named goals), runs the **planner** for each, and either **auto-applies** safe refactors (when the executor supports the repo language) or **fails the check** and surfaces concrete suggestions in the GitHub check summary and an optional PR comment.

## Setup

1. **Workspace**  
   Pass `--workspace <path>` to the CLI (default: current directory). Use the root of the codebase to analyze (e.g. repo root, or a subdirectory such as a TypeScript app). Paths under `node_modules` are never scanned.

2. **Config file**  
   Add a `.refactor-agent.yaml` (or `.refactor-agent.yml`) at the repo root. See [.refactor-agent.example.yaml](../.refactor-agent.example.yaml) for the schema. Each preset has an `id` and a `goal` (the planner prompt). Optionally set `language`, `file_ext`, or `workspace_subdir` (run this preset under a subdir of the workspace, for monorepos) per preset.

3. **Minimal setup without a file**  
   Set env var `REFACTOR_AGENT_GOAL` to a single goal string. The check will run that goal with preset id `env`.

4. **Which presets run**  
   By default all presets from the config file run. To restrict, set `REFACTOR_AGENT_PRESET` to a comma-separated list of preset ids (e.g. `layer-boundaries,vertical-slices`).

5. **Secrets**  
   The planner uses Anthropic. In GitHub Actions, configure at least:
   - `ANTHROPIC_API_KEY`
   - Optionally `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` for observability

## What the check does

- **Analyze**  
  For each preset, the planner produces a `RefactorSchedule` (goal + list of operations: rename, move symbol, move file, etc.).

- **Auto-apply**  
  Only when the executor supports the repo language (currently **TypeScript**). If the schedule has operations and the repo is TypeScript, the CI runs the executor. If it completes with no `NeedInput`, changes are applied in the job (and you can commit them or attach a patch). If execution fails or needs human input, the run falls back to report-only.

- **Report-only / fail**  
  When there are suggested operations and they were **not** auto-applied (e.g. repo is Python, or executor failed), the refactor check **fails**. The GitHub check run summary (and optional PR comment) show goal, operation count, and a list of items: file, op type, rationale.

## When the check fails

The check fails when:

- At least one preset produced suggestions and they were not all auto-applied, or  
- The executor was run but failed (e.g. partial apply, or unsupported op).

So the gate is clear: either CI applies the fixes or the developer must address the suggestions (re-run locally, apply manually, or adjust code so the planner no longer suggests those ops).

## Reading the tips

In the check run summary (and PR comment when enabled) you get:

- **Goal** – the preset goal that was run  
- **Operation count** – number of suggested ops  
- **auto_applied** – whether the executor ran and succeeded  
- **Operations table** – op type, file path, rationale for each suggestion  

Use this to decide what to refactor and where.

## Running locally

```bash
# Workspace = directory to analyze (repo root, or e.g. a TypeScript app subdir)
uv run python -m refactor_agent.ci --workspace /path/to/your/codebase

# Report-only (no auto-apply even for TypeScript)
uv run python -m refactor_agent.ci --workspace . --no-auto-apply

# Write JSON report to a file
uv run python -m refactor_agent.ci --workspace . --output json --output-file report.json
```

To reproduce this repo’s CI check (run on the TypeScript playground for verification):  
`uv run python -m refactor_agent.ci --workspace playground/typescript --output markdown --output-file report.md`

Exit code: `0` when there are no suggestions or all were auto-applied; `1` when the check would fail (suggestions not applied or execution failed).
