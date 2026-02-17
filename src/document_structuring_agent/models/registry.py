from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pydantic_ai import Agent

    from document_structuring_agent.models.classification import DocumentClassification
    from document_structuring_agent.models.nodes import DocumentNode


class ParserRegistry:
    """Registry mapping document classifications to specialized parser agents."""

    def __init__(
        self, data: dict[DocumentClassification, Agent[None, DocumentNode]]
    ) -> None:
        self._data = data

    def __getitem__(self, key: DocumentClassification) -> Agent[None, DocumentNode]:
        return self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[DocumentClassification]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(
        self,
        key: DocumentClassification,
        default: Agent[None, DocumentNode] | None = None,
    ) -> Agent[None, DocumentNode] | None:
        """Look up a parser agent by classification."""
        return self._data.get(key, default)
