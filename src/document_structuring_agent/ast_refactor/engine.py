"""AST engine: parse source, skeleton, rename_symbol and extract_function."""

from __future__ import annotations

import ast
import copy
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider, ScopeProvider

if TYPE_CHECKING:
    from collections.abc import Iterator

# ---------------------------------------------------------------------------
# Deprecated: stdlib AST engine (kept for reference, not used by agent)
# ---------------------------------------------------------------------------


@dataclass
class _ScopeInfo:
    """Per-function/class skeleton info."""

    kind: str  # "FunctionDef" or "ClassDef"
    name: str
    lineno: int
    args: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    assigns: list[str] = field(default_factory=list)


class ASTEngine:
    """Holds parsed AST and exposes skeleton, rename_symbol, and to_source.

    Deprecated. Use LibCSTEngine for new code; this implementation loses
    comments and formatting via ast.unparse. No further development.
    """

    def __init__(self, source: str) -> None:
        """Parse source into an AST. Raises SyntaxError on invalid Python."""
        warnings.warn(
            "ASTEngine is deprecated; use LibCSTEngine for lossless round-trip.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source = source
        self.tree = ast.parse(source)

    def get_skeleton(self) -> str:
        """Produce a text skeleton: function/class names, args, calls, line numbers."""
        scopes: list[_ScopeInfo] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                scopes.append(_scope_info_for_function(node))
            elif isinstance(node, ast.ClassDef):
                scopes.append(_scope_info_for_class(node))
        lines: list[str] = []
        for s in scopes:
            lines.append(f"{s.kind} '{s.name}' (line {s.lineno})")
            if s.args:
                lines.append(f"  args: {', '.join(s.args)}")
            if s.calls:
                lines.append(f"  calls: {sorted(set(s.calls))}")
            if s.assigns:
                lines.append(f"  assigns: {sorted(set(s.assigns))}")
            lines.append("")
        return "\n".join(lines).strip()

    def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol in the AST; optionally restrict to a function/class scope.

        Returns a short summary or "ERROR: symbol not found". Mutates the tree in place.
        """
        if scope_node is None:
            return _rename_file_wide(self.tree, old_name, new_name)
        return _rename_in_scope(self.tree, old_name, new_name, scope_node)

    def extract_function(
        self,
        scope_function: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
    ) -> str:
        """Extract a line range from a function into a new function; replace with call.

        The new function is inserted immediately before scope_function. Parameters
        are inferred from names used in the block but defined outside it.

        Returns a short summary or an error string. Mutates the tree in place.
        """
        return _extract_function_impl(
            self.tree,
            scope_function,
            start_line,
            end_line,
            new_function_name,
        )

    def to_source(self) -> str:
        """Return source code for the current AST."""
        return ast.unparse(self.tree)


def _scope_info_for_function(node: ast.FunctionDef) -> _ScopeInfo:
    args_list = [a.arg for a in node.args.args]
    if node.args.vararg:
        args_list.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        args_list.append(f"**{node.args.kwarg.arg}")
    calls: list[str] = []
    assigns: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _call_name(child)
            if name:
                calls.append(name)
        elif isinstance(child, ast.Assign):
            for t in child.targets:
                names = _assign_target_names(t)
                assigns.extend(names)
    return _ScopeInfo(
        kind="FunctionDef",
        name=node.name,
        lineno=node.lineno,
        args=args_list,
        calls=calls,
        assigns=assigns,
    )


def _scope_info_for_class(node: ast.ClassDef) -> _ScopeInfo:
    calls: list[str] = []
    assigns: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _call_name(child)
            if name:
                calls.append(name)
        elif isinstance(child, ast.Assign):
            for t in child.targets:
                names = _assign_target_names(t)
                assigns.extend(names)
    return _ScopeInfo(
        kind="ClassDef",
        name=node.name,
        lineno=node.lineno,
        args=[],
        calls=calls,
        assigns=assigns,
    )


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _assign_target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple):
        out: list[str] = []
        for elt in target.elts:
            out.extend(_assign_target_names(elt))
        return out
    return []


def _rename_file_wide(tree: ast.AST, old_name: str, new_name: str) -> str:
    """Rename all occurrences of old_name to new_name in the entire tree."""
    renamed_lines: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == old_name:
            node.id = new_name
            renamed_lines.append(node.lineno)
        elif (
            isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == old_name
        ):
            node.name = new_name
            renamed_lines.append(node.lineno)
        elif isinstance(node, ast.arg) and node.arg == old_name:
            node.arg = new_name
            renamed_lines.append(node.lineno)

    if not renamed_lines:
        return "ERROR: symbol not found"
    unique = sorted(set(renamed_lines))
    count = len(renamed_lines)
    lines_str = ", ".join(str(ln) for ln in unique)
    return f"Renamed {count} occurrence(s) at lines {lines_str}"


def _find_scope_node(
    tree: ast.AST, scope_name: str
) -> ast.FunctionDef | ast.ClassDef | None:
    """Return the FunctionDef or ClassDef node with the given name, or None."""
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and node.name == scope_name
        ):
            return node
    return None


def _rename_in_scope(
    tree: ast.AST,
    old_name: str,
    new_name: str,
    scope_node_name: str,
) -> str:
    """Rename old_name to new_name only within the given function/class scope."""
    scope_node = _find_scope_node(tree, scope_node_name)
    if scope_node is None:
        return "ERROR: symbol not found"

    renamed_lines: list[int] = []

    def rename_in_node(node: ast.AST) -> None:
        if isinstance(node, ast.Name) and node.id == old_name:
            node.id = new_name
            renamed_lines.append(node.lineno)
        elif (
            isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == old_name
        ):
            node.name = new_name
            renamed_lines.append(node.lineno)
        elif isinstance(node, ast.arg) and node.arg == old_name:
            node.arg = new_name
            renamed_lines.append(node.lineno)

    for node in ast.walk(scope_node):
        rename_in_node(node)

    if not renamed_lines:
        return "ERROR: symbol not found"
    unique = sorted(set(renamed_lines))
    count = len(renamed_lines)
    lines_str = ", ".join(str(ln) for ln in unique)
    return f"Renamed {count} occurrence(s) at lines {lines_str}"


# ---------------------------------------------------------------------------
# extract_function helpers
# ---------------------------------------------------------------------------


def _stmt_end_line(node: ast.stmt) -> int:
    """Last line of a statement node (1-based)."""
    return getattr(node, "end_lineno", None) or node.lineno


def _stmt_overlaps_range(node: ast.stmt, start_line: int, end_line: int) -> bool:
    """True if the statement overlaps the given inclusive line range."""
    return node.lineno <= end_line and _stmt_end_line(node) >= start_line


def _find_scope_and_parent(
    tree: ast.Module, scope_name: str
) -> tuple[ast.FunctionDef, list[ast.stmt], int] | None:
    """Return (scope_node, parent_body, index_in_parent) or None."""
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name == scope_name:
            return (node, tree.body, i)
        if isinstance(node, ast.ClassDef):
            for j, child in enumerate(node.body):
                if isinstance(child, ast.FunctionDef) and child.name == scope_name:
                    return (child, node.body, j)
    return None


def _body_statement_slice(
    body: list[ast.stmt], start_line: int, end_line: int
) -> tuple[int, int] | None:
    """Return (start_idx, end_idx) of contiguous statements overlapping the range."""
    indices: list[int] = []
    for i, stmt in enumerate(body):
        if _stmt_overlaps_range(stmt, start_line, end_line):
            indices.append(i)
    if not indices:
        return None
    return (min(indices), max(indices))


def _names_used_in_block(block: list[ast.stmt]) -> set[str]:
    """All names that are loaded (read) in the block."""
    used: set[str] = set()
    for node in ast.walk(ast.Module(body=block)):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
    return used


def _names_defined_in_block(block: list[ast.stmt]) -> set[str]:
    """Names defined (assigned or param) in the block."""
    defined: set[str] = set()
    for node in ast.walk(ast.Module(body=block)):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                defined.update(_assign_target_names(t))
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
    return defined


# Names that are builtins and should not become parameters of extracted functions.
_BUILTIN_NAMES = frozenset(
    {"print", "len", "range", "open", "str", "int", "float", "list", "dict", "set"}
)


def _param_order_from_block(block: list[ast.stmt], params: set[str]) -> list[str]:
    """Order of first use of each param name in the block."""
    order: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(ast.Module(body=block)):
        if isinstance(node, ast.Name) and node.id in params and node.id not in seen:
            seen.add(node.id)
            order.append(node.id)
    return order


def _extract_function_impl(
    tree: ast.Module,
    scope_function: str,
    start_line: int,
    end_line: int,
    new_function_name: str,
) -> str:
    """Implement extract_function; mutates tree."""
    if not isinstance(tree, ast.Module):
        return "ERROR: expected module"
    found = _find_scope_and_parent(tree, scope_function)
    if found is None:
        return f"ERROR: function {scope_function!r} not found"
    scope_node, parent_body, scope_index = found
    if not isinstance(scope_node, ast.FunctionDef):
        return "ERROR: extract_function only supports functions (not classes)"
    body = scope_node.body
    slice_result = _body_statement_slice(body, start_line, end_line)
    if slice_result is None:
        return f"ERROR: no statements in line range {start_line}-{end_line}"
    start_idx, end_idx = slice_result
    block = body[start_idx : end_idx + 1]
    used = _names_used_in_block(block)
    defined_in_block = _names_defined_in_block(block)
    free = (used - defined_in_block) - _BUILTIN_NAMES
    param_names = _param_order_from_block(block, free)
    extracted = copy.deepcopy(body[start_idx : end_idx + 1])
    new_args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg=p) for p in param_names],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    new_func = ast.FunctionDef(
        name=new_function_name,
        args=new_args,
        body=extracted,
        decorator_list=[],
        returns=None,
    )
    # Required for ast.unparse in Python 3.12+
    new_func.lineno = scope_node.lineno
    new_func.end_lineno = (
        scope_node.end_lineno
        if getattr(scope_node, "end_lineno", None) is not None
        else scope_node.lineno
    )
    call = ast.Expr(
        value=ast.Call(
            func=ast.Name(id=new_function_name, ctx=ast.Load()),
            args=[ast.Name(id=p, ctx=ast.Load()) for p in param_names],
            keywords=[],
        )
    )
    new_body = [*body[:start_idx], call, *body[end_idx + 1 :]]
    scope_node.body = new_body
    parent_body.insert(scope_index, new_func)
    return (
        f"Extracted lines {start_line}-{end_line} into {new_function_name!r}"
        f" (params: {', '.join(param_names)})."
    )


# ---------------------------------------------------------------------------
# LibCST engine (active): lossless round-trip, scope-aware rename
# ---------------------------------------------------------------------------


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
    """Holds parsed LibCST module; lossless round-trip, scope-aware rename."""

    def __init__(self, source: str) -> None:
        """Parse source into a CST. Raises cst.ParserSyntaxError on invalid Python."""
        self.source = source
        self._module = cst.parse_module(source)

    def get_skeleton(self) -> str:
        """Produce a text skeleton: function/class names, args, calls, line numbers."""
        parts: list[str] = []
        for node in self._module.body:
            if isinstance(node, cst.FunctionDef):
                parts.append(_cst_skeleton_line_for_function(self._module, node))
            elif isinstance(node, cst.ClassDef):
                parts.append(_cst_skeleton_line_for_class(self._module, node))
        return "\n\n".join(parts) if parts else ""

    def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol file-wide or within a function/class scope.

        Returns a short summary or an error string. Preserves formatting/comments.
        """
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

    def extract_function(
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

    def to_source(self) -> str:
        """Return source for the current CST (lossless except intentional edits)."""
        return self._module.code
