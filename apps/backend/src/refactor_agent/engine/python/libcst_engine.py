from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider, ScopeProvider

from refactor_agent.engine.base import CollisionInfo
from refactor_agent.engine.logger import logger

if TYPE_CHECKING:
    from collections.abc import Iterator

_BUILTIN_NAMES: frozenset[str] = frozenset(
    {"print", "len", "range", "open", "str", "int", "float", "list", "dict", "set"}
)


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
            # LibCST scope chain (metadata API returns generic scope object).
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
        except Exception as e:
            logger.debug("Scope metadata missing for node", node=type(e).__name__)
        return False

    @override
    def leave_Name(
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
        except Exception as e:
            logger.debug("Position metadata missing for Name", error=type(e).__name__)
        return updated_node.with_changes(value=self._new_name)

    @override
    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.BaseStatement | cst.CSTNode:
        if updated_node.name.value != self._old_name:
            return updated_node
        try:
            pos = self.get_metadata(PositionProvider, original_node, None)
            if pos is not None:
                self.renamed_lines.append(pos.start.line)
        except Exception as e:
            logger.debug(
                "Position metadata missing for FunctionDef", error=type(e).__name__
            )
        return updated_node.with_changes(
            name=updated_node.name.with_changes(value=self._new_name)
        )

    @override
    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.BaseStatement | cst.CSTNode:
        if updated_node.name.value != self._old_name:
            return updated_node
        try:
            pos = self.get_metadata(PositionProvider, original_node, None)
            if pos is not None:
                self.renamed_lines.append(pos.start.line)
        except Exception as e:
            logger.debug(
                "Position metadata missing for ClassDef", error=type(e).__name__
            )
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
        # LibCST scope chain (metadata API returns generic scope object).
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
    except Exception as e:
        logger.debug(
            "Scope metadata missing in _cst_node_in_scope", error=type(e).__name__
        )
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


def _cst_stmt_line_range(
    wrapper: MetadataWrapper, node: cst.CSTNode
) -> tuple[int, int]:
    """Return (start_line, end_line) for a statement node; (0, 0) if unavailable."""
    try:
        pos = wrapper.resolve(PositionProvider).get(node)
    except Exception:
        return (0, 0)
    if pos is None:
        return (0, 0)
    return (pos.start.line, pos.end.line)


def _cst_stmt_overlaps_range(
    wrapper: MetadataWrapper,
    node: cst.CSTNode,
    start_line: int,
    end_line: int,
) -> bool:
    """True if the statement overlaps the given inclusive line range."""
    stmt_start, stmt_end = _cst_stmt_line_range(wrapper, node)
    return stmt_start <= end_line and stmt_end >= start_line


def _cst_visit_assign_targets(
    used: set[str], node: cst.Assign | cst.AnnAssign | cst.AugAssign
) -> None:
    """Visit assignment targets (store) and value (load) for Assign-like nodes."""
    if isinstance(node, cst.Assign):
        for t in node.targets:
            if isinstance(t, cst.AssignTarget) and isinstance(t.target, cst.Name):
                _cst_collect_used_names(used, t.target, in_assign_target=True)
        _cst_collect_used_names(used, node.value, in_assign_target=False)
    elif isinstance(node, cst.AnnAssign) and node.target is not None:
        if isinstance(node.target, cst.Name):
            _cst_collect_used_names(used, node.target, in_assign_target=True)
        if node.value is not None:
            _cst_collect_used_names(used, node.value, in_assign_target=False)
    elif isinstance(node, cst.AugAssign):
        if isinstance(node.target, cst.Name):
            _cst_collect_used_names(used, node.target, in_assign_target=True)
        _cst_collect_used_names(used, node.value, in_assign_target=False)


def _cst_collect_used_names(
    used: set[str], node: cst.CSTNode, *, in_assign_target: bool = False
) -> None:
    """Recurse and add load names to used. Skip assignment targets."""
    if isinstance(node, cst.Name) and not in_assign_target:
        used.add(node.value)
        return
    if isinstance(node, (cst.Assign, cst.AnnAssign, cst.AugAssign)):
        _cst_visit_assign_targets(used, node)
        return
    for child in node.children:
        if isinstance(child, cst.CSTNode):
            _cst_collect_used_names(used, child, in_assign_target=in_assign_target)


def _cst_names_used_in_block(block: list[cst.BaseStatement]) -> set[str]:
    """All names that are loaded (read) in the block, excluding assignment targets."""
    used: set[str] = set()
    for stmt in block:
        _cst_collect_used_names(used, stmt, in_assign_target=False)
    return used


def _cst_walk_block(block: list[cst.BaseStatement]) -> Iterator[cst.CSTNode]:
    """Walk all nodes in a block of statements."""
    for stmt in block:
        yield from _cst_walk(stmt)


def _cst_names_defined_in_block(block: list[cst.BaseStatement]) -> set[str]:
    """Names defined (assigned or param) in the block."""
    defined: set[str] = set()
    for node in _cst_walk_block(block):
        if isinstance(node, cst.Assign):
            for t in node.targets:
                if isinstance(t, cst.AssignTarget) and isinstance(t.target, cst.Name):
                    defined.add(t.target.value)
        elif (
            isinstance(node, cst.AnnAssign) and node.target is not None
        ) or isinstance(node, cst.AugAssign):
            if isinstance(node.target, cst.Name):
                defined.add(node.target.value)
        elif isinstance(node, (cst.FunctionDef, cst.ClassDef)) or (
            isinstance(node, cst.Param) and node.name is not None
        ):
            defined.add(node.name.value)
    return defined


def _cst_param_order_from_block(
    block: list[cst.BaseStatement], params: set[str]
) -> list[str]:
    """Order of first use of each param name in the block."""
    order: list[str] = []
    seen: set[str] = set()
    for node in _cst_walk_block(block):
        if (
            isinstance(node, cst.Name)
            and node.value in params
            and node.value not in seen
        ):
            seen.add(node.value)
            order.append(node.value)
    return order


def _cst_find_scope_and_parent(
    module: cst.Module, scope_name: str
) -> tuple[cst.FunctionDef, list[cst.BaseStatement], int] | None:
    """Return (scope_node, parent_body, index_in_parent) or None."""
    for i, node in enumerate(module.body):
        if isinstance(node, cst.FunctionDef) and node.name.value == scope_name:
            if isinstance(node.body, cst.IndentedBlock):
                return (node, list(node.body.body), i)
            return None
        if isinstance(node, cst.ClassDef) and isinstance(node.body, cst.IndentedBlock):
            for j, child in enumerate(node.body.body):
                if (
                    isinstance(child, cst.FunctionDef)
                    and child.name.value == scope_name
                ):
                    if isinstance(child.body, cst.IndentedBlock):
                        return (child, list(child.body.body), j)
                    return None
    return None


def _cst_find_parent(
    module: cst.Module, scope_node: cst.FunctionDef
) -> cst.Module | cst.ClassDef | None:
    """Return the Module or ClassDef that contains scope_node, or None."""
    for node in _cst_walk(module):
        if isinstance(node, cst.ClassDef) and isinstance(node.body, cst.IndentedBlock):
            for child in node.body.body:
                if child is scope_node:
                    return node
        elif isinstance(node, cst.Module):
            for child in node.body:
                if child is scope_node:
                    return node
    return None


@dataclass
class _ExtractReplacement:
    """Data for applying an extract_function replacement."""

    scope_node: cst.FunctionDef
    new_func: cst.FunctionDef
    updated_scope: cst.FunctionDef
    err_msg: str
    summary: str


def _cst_apply_extract_replacement(
    module: cst.Module,
    parent: cst.Module | cst.ClassDef,
    repl: _ExtractReplacement,
) -> tuple[cst.Module, str]:
    """Apply the extract replacement; returns (new_module, summary)."""
    if isinstance(parent, cst.Module):
        for i, node in enumerate(module.body):
            if node is repl.scope_node:
                before = list(module.body[:i])
                after = list(module.body[i + 1 :])
                new_body = [*before, repl.new_func, repl.updated_scope, *after]
                return (module.with_changes(body=new_body), repl.summary)
    elif isinstance(parent, cst.ClassDef):
        if not isinstance(parent.body, cst.IndentedBlock):
            return (module, repl.err_msg)
        class_body = list(parent.body.body)
        for i, child in enumerate(class_body):
            if child is repl.scope_node:
                new_class_body = [
                    *class_body[:i],
                    repl.new_func,
                    repl.updated_scope,
                    *class_body[i + 1 :],
                ]
                new_parent = parent.with_changes(
                    body=cst.IndentedBlock(body=new_class_body)
                )
                new_module_body = [
                    new_parent if node is parent else node for node in module.body
                ]
                return (module.with_changes(body=new_module_body), repl.summary)
    return (module, repl.err_msg)


def _cst_extract_function_impl(
    module: cst.Module,
    scope_function: str,
    start_line: int,
    end_line: int,
    new_function_name: str,
) -> tuple[cst.Module, str]:
    """Implement extract_function; returns (new_module, summary_or_error)."""
    wrapper = MetadataWrapper(module)
    # Use wrapper.module so PositionProvider lookups succeed (metadata keys are
    # nodes from the wrapped clone, not the original module).
    wrapped = wrapper.module
    found = _cst_find_scope_and_parent(wrapped, scope_function)
    if found is None:
        return (wrapped, f"ERROR: function {scope_function!r} not found")

    scope_node, body_list, _scope_index = found
    indices: list[int] = []
    for i, stmt in enumerate(body_list):
        if _cst_stmt_overlaps_range(wrapper, stmt, start_line, end_line):
            indices.append(i)
    if not indices:
        return (
            wrapped,
            f"ERROR: no statements in line range {start_line}-{end_line}",
        )
    start_idx = min(indices)
    end_idx = max(indices)
    block = body_list[start_idx : end_idx + 1]
    used = _cst_names_used_in_block(block)
    defined_in_block = _cst_names_defined_in_block(block)
    free = (used - defined_in_block) - _BUILTIN_NAMES
    param_names = _cst_param_order_from_block(block, free)

    extracted_body = [stmt.deep_clone() for stmt in block]
    new_params = cst.Parameters(
        params=[cst.Param(name=cst.Name(p)) for p in param_names]
    )
    new_func = cst.FunctionDef(
        name=cst.Name(new_function_name),
        params=new_params,
        body=cst.IndentedBlock(body=extracted_body),
    )
    call_expr = cst.Call(
        func=cst.Name(new_function_name),
        args=[cst.Arg(value=cst.Name(p)) for p in param_names],
    )
    call_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=call_expr)])
    new_body_list = [*body_list[:start_idx], call_stmt, *body_list[end_idx + 1 :]]
    new_scope_body = cst.IndentedBlock(body=new_body_list)

    if isinstance(scope_node.body, cst.IndentedBlock):
        updated_scope = scope_node.with_changes(body=new_scope_body)
    else:
        return (wrapped, "ERROR: extract_function only supports IndentedBlock body")

    summary = (
        f"Extracted lines {start_line}-{end_line} into "
        f"{new_function_name!r} (params: {', '.join(param_names)})."
    )

    parent = _cst_find_parent(wrapped, scope_node)
    if parent is None:
        return (
            wrapped,
            f"ERROR: could not locate scope {scope_function!r} in module",
        )
    repl = _ExtractReplacement(
        scope_node=scope_node,
        new_func=new_func,
        updated_scope=updated_scope,
        err_msg=f"ERROR: could not locate scope {scope_function!r} in module",
        summary=summary,
    )
    return _cst_apply_extract_replacement(wrapped, parent, repl)


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
        scope_function: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
    ) -> str:
        """Extract a line range from a function into a new function.

        The new function is inserted immediately before scope_function.
        Parameters are inferred from names used in the block but defined outside it.
        Preserves formatting and comments.
        """
        new_module, result = _cst_extract_function_impl(
            self._module,
            scope_function,
            start_line,
            end_line,
            new_function_name,
        )
        if not result.startswith("ERROR:"):
            self._module = new_module
            self.source = new_module.code
        return result

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
