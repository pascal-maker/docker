from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider, ScopeProvider

from refactor_agent.engine.base import CollisionInfo

if TYPE_CHECKING:
    from collections.abc import Iterator


class _RenameTransformer(cst.CSTTransformer):
    """Scope-aware rename using LibCST's ScopeProvider and PositionProvider."""

    METADATA_DEPENDENCIES = (ScopeProvider, PositionProvider)

    def __init__(
        self,
        old_name: str,
        new_name: str,
        scope_name: str | None,
    ) -> None:
        self._old_name = old_name
        self._new_name = new_name
        self._scope_name = scope_name
        self.renamed_lines: list[int] = []

    def _in_target_scope(self, node: cst.CSTNode) -> bool:
        if self._scope_name is None:
            return True
        try:
            scope = self.get_metadata(ScopeProvider, node, None)
            current: object = scope
            seen: set[object] = set()
            while current is not None and id(current) not in seen:
                seen.add(id(current))
                if hasattr(current, "name") and current.name == self._scope_name:
                    return True
                parent = getattr(current, "parent", None)
                if parent is current:
                    break
                current = parent
        except Exception:  # noqa: S110 — scope/parent metadata can be missing
            pass
        return False

    def leave_Name(  # noqa: N802 — LibCST callback name
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        if updated_node.value != self._old_name or not self._in_target_scope(
            original_node
        ):
            return updated_node
        try:
            pos = self.get_metadata(PositionProvider, original_node, None)
            if pos is not None:
                self.renamed_lines.append(pos.start.line)
        except Exception:  # noqa: S110 — position metadata can be missing
            pass
        return updated_node.with_changes(value=self._new_name)

    def leave_FunctionDef(  # noqa: N802 — LibCST callback name
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.CSTNode:
        if updated_node.name.value != self._old_name:
            return updated_node
        try:
            pos = self.get_metadata(PositionProvider, original_node, None)
            if pos is not None:
                self.renamed_lines.append(pos.start.line)
        except Exception:  # noqa: S110 — position metadata can be missing
            pass
        return updated_node.with_changes(
            name=updated_node.name.with_changes(value=self._new_name)
        )

    def leave_ClassDef(  # noqa: N802 — LibCST callback name
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.CSTNode:
        if updated_node.name.value != self._old_name:
            return updated_node
        try:
            pos = self.get_metadata(PositionProvider, original_node, None)
            if pos is not None:
                self.renamed_lines.append(pos.start.line)
        except Exception:  # noqa: S110 — position metadata can be missing
            pass
        return updated_node.with_changes(
            name=updated_node.name.with_changes(value=self._new_name)
        )


def _cst_node_in_scope(
    module: cst.Module,
    node: cst.CSTNode,
    scope_name: str | None,
) -> bool:
    """True if node is in the given scope; when scope_name is None, any scope."""
    if scope_name is None:
        return True
    try:
        wrapper = MetadataWrapper(module)
        scope = wrapper.resolve(ScopeProvider).get(node)
        current: object = scope
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if (
                hasattr(current, "name")
                and getattr(current, "name", None) == scope_name
            ):
                return True
            parent = getattr(current, "parent", None)
            if parent is current:
                break
            current = parent
    except Exception:  # noqa: S110 — scope/parent metadata can be missing
        pass
    return False


def _cst_walk(node: cst.CSTNode) -> Iterator[cst.CSTNode]:
    """Recursive walk over CST nodes."""
    yield node
    for child in node.children:
        yield from _cst_walk(child)


def _cst_line_no(module: cst.Module, node: cst.CSTNode) -> int:
    """Line number for a node from PositionProvider, or 0 if unavailable."""
    try:
        wrapper = MetadataWrapper(module)
        pos = wrapper.resolve(PositionProvider).get(node)
    except Exception:
        return 0
    else:
        return pos.start.line if pos is not None else 0


def _cst_skeleton_line_for_function(module: cst.Module, node: cst.FunctionDef) -> str:
    """Single line for a FunctionDef in skeleton (args/calls)."""
    args = [
        p.name.value
        for p in node.params.params
        if isinstance(p, cst.Param) and p.name is not None
    ]
    calls = [
        child.func.value
        for child in _cst_walk(node)
        if isinstance(child, cst.Call) and isinstance(child.func, cst.Name)
    ]
    assigns = [
        t.target.value
        for child in _cst_walk(node)
        if isinstance(child, cst.Assign)
        for t in child.targets
        if isinstance(t, cst.AssignTarget) and isinstance(t.target, cst.Name)
    ]
    line_no = _cst_line_no(module, node)
    lines = [f"FunctionDef '{node.name.value}' (line {line_no})"]
    if args:
        lines.append(f"  args: {', '.join(args)}")
    if calls:
        lines.append(f"  calls: {sorted(set(calls))}")
    if assigns:
        lines.append(f"  assigns: {sorted(set(assigns))}")
    return "\n".join(lines)


def _cst_skeleton_line_for_class(module: cst.Module, node: cst.ClassDef) -> str:
    """Single block for a ClassDef in skeleton."""
    calls = [
        child.func.value
        for child in _cst_walk(node)
        if isinstance(child, cst.Call) and isinstance(child.func, cst.Name)
    ]
    assigns = [
        t.target.value
        for child in _cst_walk(node)
        if isinstance(child, cst.Assign)
        for t in child.targets
        if isinstance(t, cst.AssignTarget) and isinstance(t.target, cst.Name)
    ]
    line_no = _cst_line_no(module, node)
    lines = [f"ClassDef '{node.name.value}' (line {line_no})"]
    if calls:
        lines.append(f"  calls: {sorted(set(calls))}")
    if assigns:
        lines.append(f"  assigns: {sorted(set(assigns))}")
    return "\n".join(lines)


class LibCSTEngine:
    """Holds parsed LibCST module; lossless round-trip, scope-aware rename.

    All public methods are async to satisfy the ``RefactorEngine`` protocol.
    The actual work is CPU-bound and runs synchronously under the hood.

    Supports ``async with`` for compatibility with subprocess engines
    (enter/exit are no-ops for this in-process engine).
    """

    language: str = "python"

    def __init__(self, source: str) -> None:
        """Parse source into a CST. Raises cst.ParserSyntaxError on invalid Python."""
        self.source = source
        self._module = cst.parse_module(source)

    async def __aenter__(self) -> LibCSTEngine:
        """No-op: in-process engine needs no startup."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """No-op: in-process engine needs no cleanup."""

    async def get_skeleton(self) -> str:
        """Produce a text skeleton: function/class names, args, calls, line numbers."""
        return self._get_skeleton_sync()

    async def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol file-wide or within a function/class scope.

        Returns a short summary or an error string. Preserves formatting/comments.
        """
        return self._rename_symbol_sync(old_name, new_name, scope_node)

    async def extract_function(
        self,
        _scope_function: str,
        _start_line: int,
        _end_line: int,
        _new_function_name: str,
    ) -> str:
        """Stub: extract_function not yet implemented on LibCSTEngine."""
        return (
            "ERROR: extract_function is not yet implemented with LibCST; "
            "use the deprecated ASTEngine for extract operations."
        )

    async def check_name_collisions(
        self,
        new_name: str,
        scope_node: str | None = None,
    ) -> list[CollisionInfo]:
        """Return definitions that already use new_name in the same scope."""
        return self._check_name_collisions_sync(new_name, scope_node)

    async def to_source(self) -> str:
        """Return source for the current CST (lossless except intentional edits)."""
        return self._module.code

    # ------------------------------------------------------------------
    # Sync internals
    # ------------------------------------------------------------------

    def _get_skeleton_sync(self) -> str:
        parts: list[str] = []
        for node in self._module.body:
            if isinstance(node, cst.FunctionDef):
                parts.append(
                    _cst_skeleton_line_for_function(self._module, node),
                )
            elif isinstance(node, cst.ClassDef):
                parts.append(
                    _cst_skeleton_line_for_class(self._module, node),
                )
        return "\n\n".join(parts) if parts else ""

    def _check_name_collisions_sync(
        self,
        new_name: str,
        scope_node: str | None = None,
    ) -> list[CollisionInfo]:
        collisions: list[CollisionInfo] = []
        for node in _cst_walk(self._module):
            kind: str | None = None
            if isinstance(node, cst.FunctionDef) and node.name.value == new_name:
                kind = "FunctionDef"
            elif isinstance(node, cst.ClassDef) and node.name.value == new_name:
                kind = "ClassDef"
            elif isinstance(node, cst.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, cst.AssignTarget)
                        and isinstance(target.target, cst.Name)
                        and target.target.value == new_name
                    ):
                        kind = "Assign"
                        break
            if kind is None:
                continue
            if not _cst_node_in_scope(self._module, node, scope_node):
                continue
            line_no = _cst_line_no(self._module, node)
            collisions.append(
                CollisionInfo(location=f"line {line_no}", kind=kind),
            )
        return collisions

    def _rename_symbol_sync(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        found = any(
            (isinstance(n, cst.FunctionDef) and n.name.value == old_name)
            or (isinstance(n, cst.ClassDef) and n.name.value == old_name)
            or (isinstance(n, cst.Name) and n.value == old_name)
            for n in _cst_walk(self._module)
        )
        if not found:
            return f"ERROR: symbol '{old_name}' not found in file"

        wrapper = MetadataWrapper(self._module)
        transformer = _RenameTransformer(old_name, new_name, scope_node)
        new_module = wrapper.visit(transformer)

        if not transformer.renamed_lines:
            return f"ERROR: '{old_name}' found but no renameable nodes matched"

        self._module = new_module
        self.source = new_module.code
        scope_note = f" within scope '{scope_node}'" if scope_node else " (file-wide)"
        return (
            f"Renamed '{old_name}' → '{new_name}'{scope_note}: "
            f"{len(transformer.renamed_lines)} occurrence(s) "
            f"at lines {transformer.renamed_lines}"
        )
