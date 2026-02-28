"""Check that no function signatures use dict, Dict, or TypedDict.

Enforces CLAUDE.md: use Pydantic BaseModel or RootModel instead.
Run: python scripts/lint/check_no_dict_sig.py [paths...]
Paths default to apps/backend/, functions/, scripts/ if not specified.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Names that indicate dict-like types we want to ban in function signatures.
_BANNED_NAMES = frozenset({"dict", "Dict", "TypedDict"})


def _decorator_name(decorator: ast.expr) -> str | None:
    """Return the name/id of a decorator (e.g. 'model_validator') or None."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    return None


def _has_model_validator_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Return True if the function is decorated with @model_validator (Pydantic boundary)."""
    for dec in node.decorator_list:
        if _decorator_name(dec) == "model_validator":
            return True
    return False


def _is_dict_annotation(node: ast.AST | None) -> bool:
    """Return True if the annotation is dict, Dict, or TypedDict (including subscripted, Union)."""
    if node is None:
        return False
    if isinstance(node, ast.Name):
        return node.id in _BANNED_NAMES
    if isinstance(node, ast.Subscript):
        value = node.value
        if isinstance(value, ast.Name):
            if value.id in _BANNED_NAMES:
                return True
        elif isinstance(value, ast.Attribute):
            if value.attr in _BANNED_NAMES:
                return True
        # Check slice: Union[dict, X], Optional[dict]
        slice_val = node.slice
        if isinstance(slice_val, ast.Tuple):
            return any(_is_dict_annotation(e) for e in slice_val.elts)
        return _is_dict_annotation(slice_val)
    # Union: X | Y (BinOp with BitOr)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_dict_annotation(node.left) or _is_dict_annotation(node.right)
    return False


def _get_noqa_line(lines: list[str], def_lineno: int) -> str | None:
    """Return the line immediately before the def, or None if def is at line 1."""
    if def_lineno <= 1:
        return None
    return lines[def_lineno - 2].strip()


def _has_noqa_no_dict_sig(lines: list[str], def_lineno: int) -> bool:
    """Check if the def has # no-dict-sig (or # noqa: no-dict-sig) on line before or same line."""
    prev = _get_noqa_line(lines, def_lineno)
    if prev and "no-dict-sig" in prev:
        return True
    # Same-line
    if def_lineno <= len(lines):
        same_line = lines[def_lineno - 1].strip()
        return "no-dict-sig" in same_line
    return False


def _check_args(
    node: ast.arguments, lines: list[str], def_lineno: int
) -> list[tuple[int, str]]:
    """Collect (lineno, message) for dict annotations in args."""
    violations: list[tuple[int, str]] = []
    for arg in [*node.args, *node.kwonlyargs]:
        if _is_dict_annotation(arg.annotation):
            violations.append(
                (
                    arg.lineno,
                    f"Parameter '{arg.arg}': use Pydantic BaseModel, not dict/Dict/TypedDict",
                )
            )
    if node.vararg and _is_dict_annotation(node.vararg.annotation):
        violations.append(
            (
                node.vararg.lineno,
                f"*{node.vararg.arg}: use Pydantic BaseModel, not dict",
            )
        )
    if node.kwarg and _is_dict_annotation(node.kwarg.annotation):
        violations.append(
            (node.kwarg.lineno, f"**{node.kwarg.arg}: use Pydantic BaseModel, not dict")
        )
    return violations


def _check_file(
    path: Path,
    rel_path: str,
    allowlist_paths: set[str],
    allowlist_functions: set[str],
) -> list[tuple[int, str, str]]:
    """Check a single file. Returns list of (lineno, message, func_name)."""
    violations: list[tuple[int, str, str]] = []
    try:
        source = path.read_text()
    except OSError as e:
        return [(0, f"Cannot read file: {e}", "")]
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [(e.lineno or 0, f"Syntax error: {e}", "")]

    lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _has_model_validator_decorator(node):
                continue
            if _has_noqa_no_dict_sig(lines, node.lineno):
                continue
            func_name = node.name
            full_name = f"{rel_path}:{func_name}"
            path_allowed = rel_path in allowlist_paths or any(
                rel_path.endswith(a) or a in rel_path for a in allowlist_paths
            )
            if path_allowed or full_name in allowlist_functions:
                continue
            for lineno, msg in _check_args(node.args, lines, node.lineno):
                violations.append((lineno, msg, func_name))
            if _is_dict_annotation(node.returns):
                violations.append(
                    (
                        node.lineno,
                        "Return type: use Pydantic BaseModel, not dict/Dict/TypedDict",
                        func_name,
                    )
                )

    return violations


_EXCLUDED_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", ".ruff_cache"}


def _collect_python_files(paths: list[Path], root: Path) -> list[Path]:
    """Collect all .py files under the given paths, excluding .venv etc."""
    result: list[Path] = []
    for p in paths:
        if not p.exists():
            continue
        if p.is_file() and p.suffix == ".py":
            result.append(p)
        elif p.is_dir():
            for py in p.rglob("*.py"):
                # Skip files under excluded directories
                try:
                    rel = py.relative_to(root)
                except ValueError:
                    rel = py
                parts = rel.parts
                if any(excluded in parts for excluded in _EXCLUDED_DIRS):
                    continue
                result.append(py)
    return sorted(set(result))


def main() -> int:
    """Run the checker. Exit 1 if violations found."""
    parser = argparse.ArgumentParser(
        description="Check for dict/Dict/TypedDict in function signatures (CLAUDE.md)."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to check (default: apps/backend, functions, scripts)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="PATH[:FUNC]",
        help="Allow path or path:function_name (e.g. refactor_agent/_compat.py:_patched)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    if args.paths:
        check_paths = [root / p for p in args.paths]
    else:
        check_paths = [
            root / "apps" / "backend",
            root / "functions",
            root / "scripts",
        ]

    allowlist_paths: set[str] = set()
    allowlist_functions: set[str] = set()
    for a in args.allow:
        if ":" in a:
            allowlist_functions.add(a)
        else:
            allowlist_paths.add(a)

    # Default allowlist: _compat._patched (pydantic_ai monkey-patch)
    allowlist_paths.add("refactor_agent/_compat.py")
    allowlist_functions.add("apps/backend/src/refactor_agent/_compat.py:_patched")

    files = _collect_python_files(check_paths, root)
    all_violations: list[tuple[Path, int, str, str]] = []

    for f in files:
        try:
            rel = f.relative_to(root)
        except ValueError:
            rel = f
        rel_str = str(rel).replace("\\", "/")
        for lineno, msg, func_name in _check_file(
            f, rel_str, allowlist_paths, allowlist_functions
        ):
            all_violations.append((f, lineno, msg, func_name))

    if all_violations:
        for path, lineno, msg, func_name in all_violations:
            try:
                rel = path.relative_to(root)
            except ValueError:
                rel = path
            print(f"{rel}:{lineno}: {msg} (in {func_name})")
        print(
            f"\n{len(all_violations)} violation(s). Use Pydantic BaseModel/RootModel; see CLAUDE.md."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
