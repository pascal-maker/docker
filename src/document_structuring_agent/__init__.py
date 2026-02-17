from document_structuring_agent._compat import (
    patch_anthropic_user_location as _patch_ul,
    patch_check_object_json_schema as _patch_schema,
)

_patch_ul()
_patch_schema()
del _patch_ul, _patch_schema
