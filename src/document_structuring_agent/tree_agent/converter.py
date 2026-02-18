"""Convert a finished TreeEngine state to the StructuredDocument output type.

The converter is a pure function: it reads TreeEngine state and produces
the DocumentNode tree that the rest of the system (and downstream consumers)
expect. ANOMALOUS and UNCERTAIN nodes are included with reduced confidence
so they are visible in the output rather than silently dropped.
"""

from __future__ import annotations

from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.document import StructuredDocument
from document_structuring_agent.models.nodes import DocumentNode, NodeMetadata, NodeType
from document_structuring_agent.tree_agent.engine import TreeEngine
from document_structuring_agent.tree_agent.flat_node import FlatNode, NodeStatus

# Maps HTML tag to NodeType. Keys are lower-case tag names.
_TAG_TO_NODE_TYPE: dict[str, NodeType] = {
    "h1": NodeType.HEADING,
    "h2": NodeType.HEADING,
    "h3": NodeType.HEADING,
    "h4": NodeType.HEADING,
    "h5": NodeType.HEADING,
    "h6": NodeType.HEADING,
    "p": NodeType.PARAGRAPH,
    "table": NodeType.TABLE,
    "tr": NodeType.TABLE_ROW,
    "td": NodeType.TABLE_CELL,
    "th": NodeType.TABLE_CELL,
    "ul": NodeType.LIST,
    "ol": NodeType.LIST,
    "li": NodeType.LIST_ITEM,
    "blockquote": NodeType.BLOCKQUOTE,
    "figure": NodeType.FIGURE,
    "div": NodeType.PARAGRAPH,
    "section": NodeType.SECTION,
    "article": NodeType.SECTION,
    "hr": NodeType.PAGE_BREAK,
}

_ANOMALOUS_CONFIDENCE = 0.1
_UNCERTAIN_CONFIDENCE = 0.5


def _flat_node_to_document_node(
    fn: FlatNode, children: list[DocumentNode]
) -> DocumentNode:
    """Convert a single FlatNode to a DocumentNode."""
    node_type = _TAG_TO_NODE_TYPE.get(fn.tag, NodeType.PARAGRAPH)
    heading_level = fn.hints.heading_level

    # Title for heading-like nodes, content for paragraph-like nodes
    title: str | None = None
    content: str | None = None
    if node_type == NodeType.HEADING:
        # Strip the description wrapper to get just text
        # description format: '<h2> [bold] p3 "text here"'
        desc = fn.description
        if '"' in desc:
            title = desc.split('"', 1)[1].rstrip('"')
        else:
            title = fn.description
    elif node_type in (NodeType.PARAGRAPH, NodeType.BLOCKQUOTE):
        desc = fn.description
        if '"' in desc:
            content = desc.split('"', 1)[1].rstrip('"')

    confidence: float | None = fn.hints.confidence or None
    if fn.status == NodeStatus.ANOMALOUS:
        confidence = _ANOMALOUS_CONFIDENCE
    elif fn.status == NodeStatus.UNCERTAIN:
        confidence = _UNCERTAIN_CONFIDENCE

    metadata = NodeMetadata(
        page_start=fn.hints.page_number,
        page_end=fn.hints.page_number,
        confidence=confidence,
        data_idx_start=fn.data_idx,
        data_idx_end=fn.data_idx,
        heading_level=heading_level,
    )

    return DocumentNode(
        node_type=node_type,
        title=title,
        content=content,
        children=children,
        metadata=metadata,
    )


def _compute_num_pages(engine: TreeEngine) -> int | None:
    """Infer the total number of pages from node hints."""
    max_page = max(
        (fn.hints.page_number for fn in engine.flat_nodes.values()),
        default=None,
    )
    return max_page


def tree_engine_to_structured_document(
    engine: TreeEngine,
    source_filename: str | None,
) -> StructuredDocument:
    """Convert a finished TreeEngine state to a StructuredDocument.

    Uses iterative post-order DFS to build the DocumentNode tree bottom-up.
    ANOMALOUS and UNCERTAIN nodes are included with reduced confidence.
    The synthetic root becomes NodeType.DOCUMENT.

    Args:
        engine: The TreeEngine after the agent loop has completed.
        source_filename: Original filename to propagate to the output.

    Returns:
        StructuredDocument with the inferred document tree.
    """
    # Iterative post-order: build children before parents
    # Stack items: (node_id, is_processed)
    stack: list[tuple[str, bool]] = [(engine.root_id, False)]
    # Map node_id -> built DocumentNode (only for non-root)
    built: dict[str, DocumentNode] = {}

    while stack:
        node_id, is_processed = stack.pop()
        tn = engine.tree_nodes.get(node_id)
        if tn is None:
            continue

        if not is_processed:
            # Push self back as processed, then push children
            stack.append((node_id, True))
            for child_id in tn.children:
                stack.append((child_id, False))
        else:
            # All children have been processed
            children = [built[c] for c in tn.children if c in built]

            if node_id == engine.root_id:
                # Synthetic root → DOCUMENT node
                root_node = DocumentNode(
                    node_type=NodeType.DOCUMENT,
                    children=children,
                    metadata=NodeMetadata(
                        page_start=1,
                        page_end=_compute_num_pages(engine),
                    ),
                )
                return StructuredDocument(
                    root=root_node,
                    classification=DocumentClassification.UNKNOWN,
                    source_filename=source_filename,
                    num_pages=_compute_num_pages(engine),
                )

            fn = engine.flat_nodes.get(node_id)
            if fn is None:
                continue
            built[node_id] = _flat_node_to_document_node(fn, children)

    # Fallback: empty document (should not be reached)
    return StructuredDocument(
        root=DocumentNode(node_type=NodeType.DOCUMENT),
        classification=DocumentClassification.UNKNOWN,
        source_filename=source_filename,
    )
