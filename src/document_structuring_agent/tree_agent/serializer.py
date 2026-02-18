"""Skeleton XML serializer for the tree agent.

Generates a compact XML view of the current tree state for injection into
the agent's iteration prompt. Each node shows its ID, status, tag, and
structural hints — full HTML content is withheld to minimise token usage.

Uses an iterative DFS (explicit stack) to avoid Python recursion depth
limits on large documents. Output is capped at _MAX_SKELETON_CHARS to
prevent context overflow; deep subtrees are collapsed when the limit is
approached.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from document_structuring_agent.tree_agent.engine import TreeEngine
    from document_structuring_agent.tree_agent.flat_node import FlatNode, NodeHints

_MAX_SKELETON_CHARS = 32_000
_INDENT = "  "
_DESCRIPTION_MAX = 60


def _hint_attrs(hints: NodeHints) -> str:
    """Build XML attribute string from NodeHints."""
    parts: list[str] = [f'page="{hints.page_number}"']
    if hints.is_bold:
        parts.append('bold="true"')
    if hints.is_italic:
        parts.append('italic="true"')
    if hints.heading_level is not None:
        parts.append(f'heading_level="{hints.heading_level}"')
    return " ".join(parts)


def _node_open_tag(fn: FlatNode, depth: int) -> str:
    """Render the opening tag for a node."""
    indent = _INDENT * depth
    hint_str = _hint_attrs(fn.hints)
    desc = fn.description[:_DESCRIPTION_MAX].replace('"', "&quot;")
    return (
        f'{indent}<node id="{fn.node_id}" status="{fn.status}"'
        f' tag="{fn.tag}" {hint_str}>\n'
        f"{indent}  {desc}"
    )


def build_skeleton_xml(engine: TreeEngine) -> str:
    """Render the current tree as skeleton XML for the agent's iteration prompt.

    Uses iterative DFS. Collapses subtrees when output approaches
    _MAX_SKELETON_CHARS to prevent context overflow.

    Args:
        engine: The current TreeEngine state.

    Returns:
        Compact XML string representing the tree skeleton.
    """
    lines: list[str] = ["<root>"]
    total_chars = len("<root>")

    # Stack items: (node_id, depth, is_closing)
    stack: list[tuple[str, int, bool]] = []

    # Push root's children in reverse order for correct DFS order
    root_tn = engine.tree_nodes[engine.root_id]
    for child_id in reversed(root_tn.children):
        stack.append((child_id, 1, False))

    while stack:
        node_id, depth, is_closing = stack.pop()

        if is_closing:
            indent = _INDENT * depth
            line = f"{indent}</node>"
            lines.append(line)
            total_chars += len(line)
            continue

        fn = engine.flat_nodes.get(node_id)
        if fn is None:
            continue

        tn = engine.tree_nodes.get(node_id)
        if tn is None:
            continue

        # Check if we're approaching the limit
        if total_chars >= _MAX_SKELETON_CHARS:
            indent = _INDENT * depth
            line = f"{indent}<!-- content truncated, {len(engine.flat_nodes)} total nodes -->"
            lines.append(line)
            break

        has_children = len(tn.children) > 0

        if has_children:
            open_line = _node_open_tag(fn, depth)
            lines.append(open_line)
            total_chars += len(open_line)

            # Push closing tag first (LIFO)
            stack.append((node_id, depth, True))

            # Push children in reverse order
            for child_id in reversed(tn.children):
                stack.append((child_id, depth + 1, False))
        else:
            indent = _INDENT * depth
            desc = fn.description[:_DESCRIPTION_MAX].replace('"', "&quot;")
            hint_str = _hint_attrs(fn.hints)
            line = (
                f'{indent}<node id="{fn.node_id}" status="{fn.status}"'
                f' tag="{fn.tag}" {hint_str}>'
                f"{desc}</node>"
            )
            lines.append(line)
            total_chars += len(line)

    lines.append("</root>")
    return "\n".join(lines)
