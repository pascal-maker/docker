from __future__ import annotations

from html.parser import HTMLParser
from dataclasses import dataclass, field

from document_structuring_agent.models.ocr_input import ElementMetadata


@dataclass
class ParsedElement:
    """A single top-level HTML element extracted from OCR output."""

    tag: str
    data_idx: int | None
    html: str
    text_content: str
    metadata: ElementMetadata | None = None


class _OcrHtmlParser(HTMLParser):
    """Streaming HTML parser that extracts top-level elements with data-idx attributes."""

    def __init__(self) -> None:
        super().__init__()
        self._elements: list[ParsedElement] = []
        self._depth = 0
        self._current_tag: str | None = None
        self._current_idx: int | None = None
        self._current_html_parts: list[str] = []
        self._current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._depth == 0:
            self._current_tag = tag
            attr_dict = dict(attrs)
            idx_str = attr_dict.get("data-idx")
            self._current_idx = int(idx_str) if idx_str is not None else None
            self._current_html_parts = []
            self._current_text_parts = []

        self._depth += 1
        attrs_str = "".join(
            f' {k}="{v}"' if v is not None else f" {k}" for k, v in attrs
        )
        self._current_html_parts.append(f"<{tag}{attrs_str}>")

    def handle_endtag(self, tag: str) -> None:
        self._current_html_parts.append(f"</{tag}>")
        self._depth -= 1

        if self._depth == 0 and self._current_tag is not None:
            self._elements.append(
                ParsedElement(
                    tag=self._current_tag,
                    data_idx=self._current_idx,
                    html="".join(self._current_html_parts),
                    text_content="".join(self._current_text_parts).strip(),
                )
            )
            self._current_tag = None

    def handle_data(self, data: str) -> None:
        if self._depth > 0:
            self._current_html_parts.append(data)
            self._current_text_parts.append(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_str = "".join(
            f' {k}="{v}"' if v is not None else f" {k}" for k, v in attrs
        )
        html = f"<{tag}{attrs_str} />"

        if self._depth == 0:
            attr_dict = dict(attrs)
            idx_str = attr_dict.get("data-idx")
            idx = int(idx_str) if idx_str is not None else None
            self._elements.append(
                ParsedElement(tag=tag, data_idx=idx, html=html, text_content="")
            )
        else:
            self._current_html_parts.append(html)


def parse_ocr_html(
    html: str,
    element_metadata: dict[int, ElementMetadata],
) -> list[ParsedElement]:
    """Parse OCR HTML and attach metadata, filtering out page headers."""
    parser = _OcrHtmlParser()
    parser.feed(html)

    result: list[ParsedElement] = []
    for elem in parser._elements:
        if elem.data_idx is not None and elem.data_idx in element_metadata:
            meta = element_metadata[elem.data_idx]
            if meta.is_page_header:
                continue
            elem.metadata = meta
        result.append(elem)

    return result


def get_page_boundaries(
    elements: list[ParsedElement],
) -> dict[int, list[ParsedElement]]:
    """Group parsed elements by page number."""
    pages: dict[int, list[ParsedElement]] = {}
    for elem in elements:
        if elem.metadata is not None:
            page = elem.metadata.page_number
            pages.setdefault(page, []).append(elem)
    return pages
