# pydantic-ai incompatibility with anthropic SDK >= 0.80.0

## Summary

`pydantic-ai` (tested on 0.8.1 and 1.59.0/1.60.0) fails to import when used with `anthropic >= 0.80.0` because it imports a `UserLocation` type that was removed from the beta module in the anthropic SDK.

## Error

```
ImportError: cannot import name 'UserLocation' from 'anthropic.types.beta.beta_web_search_tool_20250305_param'
```

Full traceback:

```
Traceback (most recent call last):
  File ".venv/lib/python3.12/site-packages/pydantic_ai/models/anthropic.py", line 143, in <module>
    from anthropic.types.beta.beta_web_search_tool_20250305_param import UserLocation
ImportError: cannot import name 'UserLocation' from 'anthropic.types.beta.beta_web_search_tool_20250305_param'

The above exception was the direct cause of the following exception:

ImportError: Please install `anthropic` to use the Anthropic model, you can use the `anthropic` optional group — `pip install "pydantic-ai-slim[anthropic]"`
```

The `try/except ImportError` block in pydantic-ai re-raises with a misleading message suggesting anthropic isn't installed, when in reality the type simply doesn't exist in the installed version.

## Root cause

### What pydantic-ai does

In [`pydantic_ai_slim/pydantic_ai/models/anthropic.py`](https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/models/anthropic.py), the import block contains:

```python
from anthropic.types.beta.beta_web_search_tool_20250305_param import UserLocation
```

### What changed in anthropic SDK 0.80.0

In `anthropic < 0.80.0` (e.g. 0.79.0), the file `anthropic/types/beta/beta_web_search_tool_20250305_param.py` contained a `UserLocation` class directly:

```python
# anthropic <= 0.79.0 — anthropic/types/beta/beta_web_search_tool_20250305_param.py
__all__ = ["BetaWebSearchTool20250305Param", "UserLocation"]

class UserLocation(TypedDict, total=False):
    type: Required[Literal["approximate"]]
    city: Optional[str]
    country: Optional[str]
    region: Optional[str]
    timezone: Optional[str]

class BetaWebSearchTool20250305Param(TypedDict, total=False):
    ...
    user_location: Optional[UserLocation]
```

In `anthropic 0.80.0` (released Feb 17, 2026 — the "Claude Sonnet 4.6" release), the `UserLocation` class was **removed** from the beta module and replaced with `BetaUserLocationParam` in a separate file:

```python
# anthropic 0.80.0 — anthropic/types/beta/beta_web_search_tool_20250305_param.py
__all__ = ["BetaWebSearchTool20250305Param"]  # UserLocation no longer here

from .beta_user_location_param import BetaUserLocationParam

class BetaWebSearchTool20250305Param(TypedDict, total=False):
    ...
    user_location: Optional[BetaUserLocationParam]  # uses new type name
```

The new type lives at:
```python
# anthropic 0.80.0 — anthropic/types/beta/beta_user_location_param.py
class BetaUserLocationParam(TypedDict, total=False):
    type: Required[Literal["approximate"]]
    city: Optional[str]
    country: Optional[str]
    region: Optional[str]
    timezone: Optional[str]
```

The **non-beta** module (`anthropic/types/web_search_tool_20250305_param.py`) still exports `UserLocation` in all versions. The breaking change only affects the beta import path.

A new web search tool version `BetaWebSearchTool20260209Param` (type `web_search_20260209`) was also added in 0.80.0, also referencing `BetaUserLocationParam`.

## Versions tested

| pydantic-ai | anthropic | Result |
|-------------|-----------|--------|
| 0.8.1       | 0.77.1    | Works  |
| 0.8.1       | 0.80.0    | Broken |
| 1.59.0      | 0.80.0    | Broken |
| 1.60.0      | 0.80.0    | Broken |

pydantic-ai-slim declares `anthropic>=0.61.0` as its dependency constraint (bumped to `>=0.78.0` after PR #4216), so the resolver installs 0.80.0 which then fails at runtime.

## Repositories and related issues/PRs

### pydantic/pydantic-ai

| # | Title | Status | Date | Relevance |
|---|-------|--------|------|-----------|
| [PR #4345](https://github.com/pydantic/pydantic-ai/pull/4345) | "Upgrade anthropic to 0.80.0, add Claude Sonnet 4.6" | **Open** | 2026-02-17 | **Direct fix.** Bumps to `anthropic>=0.80.0`, changes import from `UserLocation` to `BetaUserLocationParam`. Author: DouweM (maintainer). |
| [PR #4216](https://github.com/pydantic/pydantic-ai/pull/4216) | "Add Claude Opus 4.6, `anthropic_effort` and `anthropic_thinking.type='adaptive'`" | Merged | 2026-02-05 | Bumped anthropic to `>=0.78.0`. Did not anticipate the 0.80.0 rename. |
| [PR #4300](https://github.com/pydantic/pydantic-ai/pull/4300) | "Add anthropic speed, `fast` mode for opus 4.6" | Open | — | Related to anthropic 0.79.0 features, not the UserLocation issue. |
| [#4242](https://github.com/pydantic/pydantic-ai/issues/4242) | "Anthropic WebSearch splits response into separate text parts" | Closed | — | Web search related but not about the import. |
| [#2600](https://github.com/pydantic/pydantic-ai/issues/2600) | "Anthropic `stop_reason` `pause_turn` is not handled correctly" | Open | — | Builtin tool related, not the import. |

No standalone bug report was filed about the `UserLocation` import failure. PR #4345 was opened proactively by the maintainer on the same day anthropic 0.80.0 was released.

### anthropics/anthropic-sdk-python

| # | Title | Status | Date | Relevance |
|---|-------|--------|------|-----------|
| [v0.80.0 release](https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.80.0) | "Releasing claude-sonnet-4-6" | Released | 2026-02-17 | Contains the breaking commit `d518d6e`: extracted `UserLocation` → `BetaUserLocationParam`. Not documented as a breaking change in the release notes. |
| [#995](https://github.com/anthropics/anthropic-sdk-python/issues/995) | "Country code SG is not supported" for web search | Open | 2025-11-16 | Mentions `UserLocation` usage but is about unsupported country codes. |
| [#1170](https://github.com/anthropics/anthropic-sdk-python/issues/1170) | "Tool runner exits early when response contains only server tool use blocks" | Open | 2026-02-08 | Web search tool behavior, not types. |

No issues or PRs in the anthropic SDK repo discuss the `UserLocation` → `BetaUserLocationParam` rename as a breaking change. It was part of a larger API spec update commit and was not called out in the changelog.

## Timeline

| Date | Event |
|------|-------|
| 2026-02-05 | anthropic SDK 0.78.0 released (Opus 4.6, adaptive thinking) |
| 2026-02-05 | pydantic-ai PR #4216 merged, bumping to `anthropic>=0.78.0` |
| 2026-02-07 | anthropic SDK 0.79.0 released (fast-mode for Opus 4.6) |
| **2026-02-17** | **anthropic SDK 0.80.0 released — `UserLocation` removed from beta module, replaced by `BetaUserLocationParam`** |
| **2026-02-17** | **pydantic-ai PR #4345 opened by DouweM to fix the import and bump to `>=0.80.0`** |

## Suggested fix

PR #4345 changes the import in `pydantic_ai_slim/pydantic_ai/models/anthropic.py`:

```python
# Before (broken with anthropic >= 0.80.0):
from anthropic.types.beta.beta_web_search_tool_20250305_param import UserLocation

# After (PR #4345):
from anthropic.types.beta.beta_user_location_param import BetaUserLocationParam
```

And updates usage in `_add_builtin_tools()`:
```python
# Before:
user_location = UserLocation(type='approximate', **tool.user_location)
# After:
user_location = BetaUserLocationParam(type='approximate', **tool.user_location)
```

## Workaround

Pin `anthropic<0.80.0` until PR #4345 is merged and released:

```toml
dependencies = [
    "pydantic-ai",
    "anthropic<0.80.0",  # pinned: 0.80+ breaks pydantic-ai (UserLocation import removed from beta module, PR #4345 pending)
]
```
