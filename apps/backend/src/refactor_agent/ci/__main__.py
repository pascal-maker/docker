"""CLI entry point for refactor-agent CI check (python -m refactor_agent.ci)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from refactor_agent._log_config import configure_logging
from refactor_agent.ci.runner import run_ci
from refactor_agent.observability.langfuse_config import init_langfuse

# Load .env from cwd so local runs pick up ANTHROPIC_API_KEY etc. without exporting.
load_dotenv()
configure_logging()
# Initialize Langfuse so PydanticAI agent runs (planner) send traces.
init_langfuse()

if TYPE_CHECKING:
    from refactor_agent.ci.report import CiReport


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run refactor-agent presets (plan, optionally execute) for CI.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root (default: current directory).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to .refactor-agent.yaml (default: look under workspace).",
    )
    parser.add_argument(
        "--no-auto-apply",
        action="store_true",
        help="Report-only: do not run executor even when language is supported.",
    )
    parser.add_argument(
        "--output",
        choices=("json", "markdown"),
        default="json",
        help="Output format for report (default: json).",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Write report to this file (default: stdout).",
    )
    return parser.parse_args()


def _report_markdown(report: CiReport) -> str:
    """Render CiReport as markdown for check summary or PR comment."""
    lines = ["## Refactor check\n"]
    if report.failed:
        lines.append("**Result:** ❌ Suggestions found (not auto-applied or failed).\n")
    else:
        lines.append("**Result:** ✅ No suggestions or all auto-applied.\n")
    for pr in report.preset_results:
        lines.append(f"### {pr.preset_id}: {pr.goal}\n")
        if pr.error:
            lines.append(f"- **Error:** {pr.error}\n")
        lines.append(
            f"- Operations: {pr.operation_count} (auto_applied={pr.auto_applied})\n"
        )
        if pr.operations:
            lines.append("\n| Op | File | Rationale |\n|----|------|----------|\n")
            for op in pr.operations:
                rat = (op.rationale or "").replace("|", "\\|")[:80]
                fp = (op.file_path or "").replace("|", "\\|")[:60]
                lines.append(f"| {op.op} | {fp} | {rat} |\n")
        lines.append("\n")
    return "".join(lines)


async def _main() -> int:
    args = _parse_args()
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        sys.stderr.write(f"Error: workspace is not a directory: {workspace}\n")
        return 2
    report = await run_ci(
        workspace=workspace,
        config_path=args.config,
        auto_apply=not args.no_auto_apply,
    )
    if args.output == "json":
        out = report.model_dump_json(indent=2)
    else:
        out = _report_markdown(report)
    if args.output_file:
        args.output_file.write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out + "\n")
    return 1 if report.failed else 0


def main() -> None:
    """Entry point: run CI and exit with 0 (success) or 1 (check failed)."""
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
