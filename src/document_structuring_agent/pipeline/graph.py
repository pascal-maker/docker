from __future__ import annotations

from typing import TYPE_CHECKING

from langfuse import get_client, observe, propagate_attributes
from pydantic_graph import Graph

from document_structuring_agent.agents.parsers.registry import build_parser_registry
from document_structuring_agent.langfuse_config import init_langfuse
from document_structuring_agent.pipeline.nodes import (
    AssemblyNode,
    ClassificationNode,
    IntakeNode,
    SegmentationNode,
    SpecializedParsingNode,
)
from document_structuring_agent.pipeline.state import PipelineDeps, PipelineState

if TYPE_CHECKING:
    from document_structuring_agent.models.document import StructuredDocument
    from document_structuring_agent.models.ocr_input import OcrDocument

pipeline_graph = Graph(
    nodes=[
        IntakeNode,
        SegmentationNode,
        ClassificationNode,
        SpecializedParsingNode,
        AssemblyNode,
    ],
)


@observe()
async def process_document(ocr_document: OcrDocument) -> list[StructuredDocument]:
    """Main entrypoint: process an OCR document through the full pipeline."""
    init_langfuse()

    get_client()
    with propagate_attributes(
        tags=["document-structuring"],
        metadata={"source_filename": ocr_document.source_filename or ""},
    ):
        state = PipelineState(ocr_document=ocr_document)
        deps = PipelineDeps(parser_registry=build_parser_registry())

        result = await pipeline_graph.run(
            IntakeNode(),
            state=state,
            deps=deps,
        )

        return result.output
