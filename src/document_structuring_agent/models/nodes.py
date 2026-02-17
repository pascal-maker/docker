from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class NodeType(str, Enum):
    DOCUMENT = "document"
    SEGMENT = "segment"
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    FIGURE = "figure"
    BLOCKQUOTE = "blockquote"
    SIGNATURE_BLOCK = "signature_block"
    PAGE_BREAK = "page_break"


class NodeMetadata(BaseModel):
    page_start: int | None = None
    page_end: int | None = None
    confidence: float | None = None
    data_idx_start: int | None = None
    data_idx_end: int | None = None
    heading_level: int | None = None


class DocumentNode(BaseModel):
    node_type: NodeType
    title: str | None = None
    content: str | None = None
    children: list[DocumentNode] = []
    metadata: NodeMetadata = NodeMetadata()
