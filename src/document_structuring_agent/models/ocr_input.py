from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, RootModel

if TYPE_CHECKING:
    from collections.abc import Iterator


class ElementMetadata(BaseModel):
    """Per-element metadata from OCR, keyed by data-idx."""

    page_number: int
    confidence: float = Field(ge=0.0, le=1.0)
    left: float = 0
    top: float = 0
    width: float = 0
    height: float = 0
    is_bold: bool = False
    is_italic: bool = False
    font_family: str | None = None
    is_page_header: bool = False


class ElementMetadataMap(RootModel[dict[int, ElementMetadata]]):
    """Map of data-idx to element metadata."""

    def __getitem__(self, key: int) -> ElementMetadata:
        return self.root[key]

    def __contains__(self, key: object) -> bool:
        return key in self.root

    def __iter__(self) -> Iterator[int]:  # type: ignore[override]
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def items(self) -> Iterator[tuple[int, ElementMetadata]]:
        """Iterate over (data-idx, metadata) pairs."""
        yield from self.root.items()

    def get(
        self, key: int, default: ElementMetadata | None = None
    ) -> ElementMetadata | None:
        """Get metadata by data-idx, returning default if not found."""
        return self.root.get(key, default)


class OcrDocument(BaseModel):
    """The full input: HTML content + per-element metadata."""

    html: str
    element_metadata: ElementMetadataMap
    source_filename: str | None = None
