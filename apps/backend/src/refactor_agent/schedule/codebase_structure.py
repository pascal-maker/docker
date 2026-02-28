"""Build the full codebase structure string for the planner prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from refactor_agent.engine.registry import EngineRegistry
from refactor_agent.engine.subprocess_engine import SubprocessError
from refactor_agent.engine.typescript.ts_morph_engine import TsMorphProjectEngine

if TYPE_CHECKING:
    from pathlib import Path

    from refactor_agent.orchestrator.deps import OrchestratorDeps


def _scan_workspace(
    workspace: Path,
    file_ext: str,
) -> list[Path]:
    """Return sorted workspace files matching the extension pattern.

    Paths under node_modules (or containing that segment) are excluded.
    """
    if not workspace.exists():
        return []
    files = workspace.rglob(file_ext)
    excluded = [p for p in files if "node_modules" not in p.parts]
    return sorted(excluded)


async def build_codebase_structure(deps: OrchestratorDeps) -> str:
    r"""Build the single string (skeletons per file) to inject into the planner prompt.

    Resolves workspace files via workspace.rglob(file_ext). For TypeScript uses
    one TsMorphProjectEngine and get_skeleton per file; for other languages uses
    EngineRegistry per file. Format: one block per file,
    "## <relative_path>\n<skeleton_text>\n", concatenated.
    """
    files = _scan_workspace(deps.workspace, deps.file_ext)
    if not files:
        return "(no matching files in workspace)"

    blocks: list[str] = []

    if deps.language == "typescript":
        try:
            async with TsMorphProjectEngine(deps.workspace) as eng:
                for path in files:
                    abs_path = str(path.resolve())
                    try:
                        skeleton = await eng.get_skeleton(abs_path)
                    except SubprocessError:
                        skeleton = "(skeleton unavailable)"
                    rel = str(path.relative_to(deps.workspace))
                    blocks.append(f"## {rel}\n{skeleton}\n")
        except SubprocessError:
            blocks.append("(TypeScript project skeleton unavailable)")
    else:
        for path in files:
            rel = str(path.relative_to(deps.workspace))
            try:
                source = path.read_text(encoding="utf-8")
                engine = EngineRegistry.create(deps.language, source)
            except Exception:
                blocks.append(f"## {rel}\n(parse failed)\n")
                continue
            try:
                async with engine:
                    skeleton = await engine.get_skeleton()
            except Exception:
                skeleton = "(skeleton unavailable)"
            blocks.append(f"## {rel}\n{skeleton}\n")

    return "\n".join(blocks)
