from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ConfigDict, RootModel
from pydantic_ai import Agent

from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.nodes import DocumentNode

if TYPE_CHECKING:
    from collections.abc import Iterator


class ParserRegistry(
    RootModel[dict[DocumentClassification, Agent[None, DocumentNode]]]
):
    """Registry mapping document classifications to specialized parser agents."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __getitem__(self, key: DocumentClassification) -> Agent[None, DocumentNode]:
        return self.root[key]

    def __contains__(self, key: object) -> bool:
        return key in self.root

    def __iter__(self) -> Iterator[DocumentClassification]:  # type: ignore[override]
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def get(
        self,
        key: DocumentClassification,
        default: Agent[None, DocumentNode] | None = None,
    ) -> Agent[None, DocumentNode] | None:
        """Look up a parser agent by classification."""
        return self.root.get(key, default)
