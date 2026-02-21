"""Compatibility patches for pydantic-ai + anthropic SDK issues.

Applied at import time from __init__.py, before any pydantic-ai code runs.

1. anthropic >= 0.80 renamed UserLocation → BetaUserLocationParam but
   pydantic-ai <= 1.60.0 still imports the old name.

2. pydantic-ai <= 1.60.0's check_object_json_schema returns a bare $ref
   for recursive Pydantic models (like DocumentNode with self-referencing
   children). The Anthropic API rejects this because input_schema is
   missing "type": "object" at the root.
"""

from __future__ import annotations


def patch_anthropic_user_location() -> None:
    try:
        from anthropic.types.beta.beta_web_search_tool_20250305_param import (
            UserLocation,
        )
    except ImportError:
        import anthropic.types.beta.beta_web_search_tool_20250305_param as mod
        from anthropic.types.beta.beta_user_location_param import BetaUserLocationParam

        mod.UserLocation = BetaUserLocationParam  # type: ignore[misc]


def patch_check_object_json_schema() -> None:
    """Patch pydantic-ai to inline $ref at the root of tool schemas.

    When a recursive Pydantic model is used as output_type, the generated
    JSON schema has {"$ref": "#/$defs/Model", "$defs": {...}} at the root
    with no "type": "object". The Anthropic API requires "type" to be present.

    This patch resolves the $ref by merging the referenced definition into
    the root, keeping $defs for any nested $ref usage.
    """
    import pydantic_ai._utils as utils

    _original = utils.check_object_json_schema

    def _patched(schema):  # type: ignore[no-untyped-def]
        result = _original(schema)
        # If the result still has a bare $ref at the root (no "type"), inline it.
        if result.get("type") != "object" and (ref := result.get("$ref")):
            prefix = "#/$defs/"
            if ref.startswith(prefix):
                def_name = ref[len(prefix) :]
                defs = result.get("$defs", {})
                if (resolved := defs.get(def_name)) and resolved.get(
                    "type"
                ) == "object":
                    # Merge the resolved definition into the root, keeping $defs
                    return {**resolved, "$defs": defs}
        return result

    utils.check_object_json_schema = _patched
