"""Build operation-type documentation from schedule models for the planner prompt."""

from __future__ import annotations

from typing import get_args

from pydantic import BaseModel  # noqa: TC002 — used at runtime for model_fields

from refactor_agent.schedule.models import RefactorOperation

# Optional extra guidance per op (can grow; language/engine-specific later).
OP_HINTS: dict[str, str] = {
    "remove_node": (
        "symbol_name must be the exact declaration name as in source (e.g. "
        "MyClass, myFunc), not the filename or kebab-case."
    ),
    "move_symbol": (
        "Move one declaration between files (use when extracting a single "
        "symbol). symbol_name must be the exact declaration name as in source "
        "(e.g. MyClass, myFunc), not the filename or kebab-case."
    ),
    "move_file": (
        "Move an entire file. Updates all import paths across the project. "
        "Parent directories are created on write. Prefer move_file over "
        "move_symbol when the whole file should relocate."
    ),
    "organize_imports": "Sort and remove unused imports in a file.",
    "create_file": (
        "Create a new file with the given content. Use only for files that "
        "need actual content (e.g. barrel index.ts, new modules). Do NOT use "
        "create_file just to create directories; move_file creates parent dirs."
    ),
}


def _op_name_from_model(model: type[BaseModel]) -> str | None:
    """Return the discriminator value (op name) for a RefactorOperation model."""
    fields = model.model_fields
    op_field = fields.get("op")
    if op_field is None:
        return None
    default = op_field.default
    return str(default) if isinstance(default, str) else None


def _field_doc_name(name: str, model: type[BaseModel]) -> str:
    """Return the serialization name (alias) or field name for a field."""
    fields = model.model_fields
    finfo = fields.get(name)
    if finfo is not None and finfo.serialization_alias:
        return str(finfo.serialization_alias)
    return name


def _format_op_spec(model: type[BaseModel]) -> str:
    """Format one operation type: op name, fields, optional hint."""
    op_name = _op_name_from_model(model)
    if op_name is None:
        return ""
    fields = model.model_fields
    # Exclude "op" (discriminator); list required then optional
    required: list[str] = []
    optional: list[str] = []
    for fname, finfo in fields.items():
        if fname == "op":
            continue
        doc_name = _field_doc_name(fname, model)
        if finfo.is_required():
            required.append(doc_name)
        else:
            optional.append(doc_name)
    parts = required + [f"optional {x}" for x in optional]
    line = f"- {op_name}: {', '.join(parts)}"
    hint = OP_HINTS.get(op_name)
    if hint:
        line += f" — {hint}"
    else:
        doc = (model.__doc__ or "").strip()
        if doc:
            # First sentence or first line
            first = doc.split("\n")[0].split(". ")[0].strip()
            if first:
                line += f" — {first}"
    return line


def build_operation_types_documentation() -> str:
    """Build the operation types section from RefactorOperation models.

    Introspects the RefactorOperation union and each op model to list op names
    and fields. Can be extended later to filter by language/engine.
    """
    annotated_args = get_args(RefactorOperation)
    if not annotated_args:
        return ""
    union_type = annotated_args[0]
    op_models = get_args(union_type)
    lines = [_format_op_spec(m) for m in op_models if _op_name_from_model(m)]
    return "\n".join(lines)
