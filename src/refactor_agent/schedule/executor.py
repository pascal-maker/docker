"""Execute a RefactorSchedule: validate, topo sort, run operations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from refactor_agent.engine.typescript.ts_morph_engine import TsMorphProjectEngine
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.models import (
    CreateFileOp,
    MoveFileOp,
    MoveSymbolOp,
    OrganizeImportsOp,
    RefactorOperation,
    RefactorSchedule,
    RemoveNodeOp,
    RenameOp,
)


@dataclass
class OpResult:
    """Result of executing a single operation."""

    op_id: str | None
    op_type: str
    summary: str
    success: bool


@dataclass
class ScheduleResult:
    """Result of executing a full schedule."""

    success: bool
    results: list[OpResult]
    error: str | None = None


def _resolve_path(workspace: Path, rel_path: str) -> Path:
    """Resolve a path relative to workspace; ensure it stays under workspace."""
    path = (workspace / rel_path).resolve()
    try:
        path.relative_to(workspace)
    except ValueError:
        raise ValueError(f"Path {rel_path!r} is outside workspace") from None
    return path


def _assign_ids(schedule: RefactorSchedule) -> list[tuple[str, RefactorOperation]]:
    """Assign an id to each op (use existing or index). Returns list of (id, op)."""
    out: list[tuple[str, RefactorOperation]] = []
    for i, op in enumerate(schedule.operations):
        op_id = op.id or str(i)
        out.append((op_id, op))
    return out


def _validate_and_topo(
    schedule: RefactorSchedule,
) -> tuple[list[tuple[str, RefactorOperation]], str | None]:
    """Validate ids/depends_on and return topo-ordered (id, op) or error message."""
    id_to_op = dict(_assign_ids(schedule))
    ids = set(id_to_op)

    # Check all depends_on exist
    for op_id, op in id_to_op.items():
        for dep in op.depends_on:
            if dep not in ids:
                return [], f"Operation {op_id!r} depends on unknown id {dep!r}"

    # Build adjacency: op_id -> list of ids that must run after it (its dependents)
    # So we need order such that for each (op, dep), dep runs before op.
    # Topo: we want A before B if B depends_on A. So in_degree = number of deps.
    in_degree: dict[str, int] = {}
    for op_id, op in id_to_op.items():
        in_degree[op_id] = len(op.depends_on)

    # op_id depends_on [dep1, dep2] means dep1, dep2 run before op_id.
    # Successors: dep -> [op_ids that depend on dep].
    succ: dict[str, list[str]] = {i: [] for i in ids}
    for op_id, op in id_to_op.items():
        for dep in op.depends_on:
            succ[dep].append(op_id)

    # Kahn's algorithm: start with in_degree 0, then decrement successors.
    queue = deque(i for i in ids if in_degree[i] == 0)
    order: list[str] = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for s in succ[n]:
            in_degree[s] -= 1
            if in_degree[s] == 0:
                queue.append(s)

    if len(order) != len(ids):
        return [], "Cycle detected in depends_on"

    return [(i, id_to_op[i]) for i in order], None


async def _run_one(
    op_id: str,
    op: RefactorOperation,
    workspace: Path,
) -> OpResult:
    """Run a single operation (TypeScript only for PoC)."""
    if isinstance(op, MoveFileOp):
        return OpResult(
            op_id,
            "move_file",
            "Skipped: move_file not implemented",
            success=False,
        )
    if isinstance(op, CreateFileOp):
        return OpResult(
            op_id,
            "create_file",
            "Skipped: create_file not implemented",
            success=False,
        )

    if isinstance(op, RenameOp):
        async with TsMorphProjectEngine(workspace) as eng:
            fp = _resolve_path(workspace, op.file_path)
            result = await eng.rename_symbol(
                str(fp),
                op.old_name,
                op.new_name,
                op.scope_node,
            )
            await eng.apply_changes()
            return OpResult(op_id, "rename", result, success="ERROR" not in result)

    if isinstance(op, MoveSymbolOp):
        async with TsMorphProjectEngine(workspace) as eng:
            src = _resolve_path(workspace, op.source_file)
            tgt = _resolve_path(workspace, op.target_file)
            result = await eng.move_symbol(
                str(src),
                str(tgt),
                op.symbol_name,
            )
            await eng.apply_changes()
            return OpResult(
                op_id,
                "move_symbol",
                result,
                success="ERROR" not in result,
            )

    if isinstance(op, RemoveNodeOp):
        async with TsMorphProjectEngine(workspace) as eng:
            fp = _resolve_path(workspace, op.file_path)
            result = await eng.remove_node(
                str(fp),
                op.symbol_name,
                op.kind,
            )
            await eng.apply_changes()
            return OpResult(
                op_id,
                "remove_node",
                result,
                success="ERROR" not in result,
            )

    if isinstance(op, OrganizeImportsOp):
        async with TsMorphProjectEngine(workspace) as eng:
            fp = _resolve_path(workspace, op.file_path)
            result = await eng.organize_imports(str(fp))
            await eng.apply_changes()
            return OpResult(op_id, "organize_imports", result, success=True)

    raise AssertionError(f"Unhandled operation type: {type(op).__name__}")


async def execute_schedule(
    schedule: RefactorSchedule,
    deps: OrchestratorDeps,
) -> ScheduleResult:
    """Validate, topo sort, and run all operations in the schedule.

    TypeScript only for PoC. move_file and create_file are skipped.
    """
    ordered, err = _validate_and_topo(schedule)
    if err:
        return ScheduleResult(success=False, results=[], error=err)

    workspace = deps.workspace
    if deps.language != "typescript":
        return ScheduleResult(
            success=False,
            results=[],
            error="Schedule executor supports TypeScript only in PoC",
        )

    results: list[OpResult] = []
    for op_id, op in ordered:
        try:
            res = await _run_one(op_id, op, workspace)
            results.append(res)
            if not res.success and "Skipped" not in res.summary:
                return ScheduleResult(
                    success=False,
                    results=results,
                    error=res.summary,
                )
        except Exception as e:
            return ScheduleResult(
                success=False,
                results=results,
                error=str(e),
            )

    return ScheduleResult(success=True, results=results)
