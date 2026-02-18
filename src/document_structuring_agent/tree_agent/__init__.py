"""Tree agent: agentic alternative to the prompt-pipeline.

Exposes a single async entry point run_tree_agent() that accepts an
OcrDocument and returns a StructuredDocument — the same types the existing
pipeline uses. The existing pipeline is not modified.
"""

from __future__ import annotations

from document_structuring_agent.tree_agent.agent import run_tree_agent

__all__ = ["run_tree_agent"]
