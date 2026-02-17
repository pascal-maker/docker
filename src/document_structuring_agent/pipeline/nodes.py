from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_graph import BaseNode, End, GraphRunContext

from document_structuring_agent.agents.classification import create_classification_agent
from document_structuring_agent.agents.segmentation import create_segmentation_agent
from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.document import StructuredDocument
from document_structuring_agent.models.nodes import DocumentNode, NodeMetadata, NodeType
from document_structuring_agent.models.ocr_input import ElementMetadataMap
from document_structuring_agent.models.segmentation import DocumentSegment
from document_structuring_agent.pipeline.state import PipelineDeps, PipelineState
from document_structuring_agent.preprocessing.html_parser import parse_ocr_html

if TYPE_CHECKING:
    from document_structuring_agent.models.ocr_input import ElementMetadata
    from document_structuring_agent.preprocessing.html_parser import ParsedElement

_SMALL_DOCUMENT_THRESHOLD = 50


@dataclass
class IntakeNode(BaseNode[PipelineState, PipelineDeps, list[StructuredDocument]]):
    """Parse OCR HTML, attach metadata, filter page headers."""

    async def run(
        self, ctx: GraphRunContext[PipelineState, PipelineDeps]
    ) -> SegmentationNode:
        """Parse HTML and attach per-element OCR metadata."""
        doc = ctx.state.ocr_document
        ctx.state.parsed_elements = parse_ocr_html(doc.html, doc.element_metadata)
        return SegmentationNode()


@dataclass
class SegmentationNode(BaseNode[PipelineState, PipelineDeps, list[StructuredDocument]]):
    """Rule-based pre-segmentation + LLM refinement."""

    async def run(
        self, ctx: GraphRunContext[PipelineState, PipelineDeps]
    ) -> ClassificationNode:
        """Segment the document using rules then optionally LLM refinement."""
        segments = _rule_based_segmentation(ctx.state.parsed_elements)

        if (
            len(segments) <= 1
            and len(ctx.state.parsed_elements) < _SMALL_DOCUMENT_THRESHOLD
        ):
            # Small document, skip LLM segmentation
            ctx.state.segments = segments
            ctx.state.num_documents_detected = 1
            return ClassificationNode()

        # Use LLM agent for refinement
        agent = create_segmentation_agent()
        elements_summary = _build_elements_summary(ctx.state.parsed_elements)
        prompt = (
            "Here are the document elements with "
            f"preliminary segmentation:\n\n{elements_summary}"
        )
        result = await agent.run(prompt)
        segmentation = result.output

        ctx.state.segments = segmentation.segments
        ctx.state.num_documents_detected = segmentation.num_documents_detected
        return ClassificationNode()


@dataclass
class ClassificationNode(
    BaseNode[PipelineState, PipelineDeps, list[StructuredDocument]]
):
    """Classify each segment using the LLM agent."""

    async def run(
        self, ctx: GraphRunContext[PipelineState, PipelineDeps]
    ) -> SpecializedParsingNode:
        """Classify each segment via the classification agent."""
        agent = create_classification_agent()

        for segment in ctx.state.segments:
            preview = segment.html[:3000]
            result = await agent.run(f"Classify this document segment:\n\n{preview}")
            segment.classification = result.output.classification

        return SpecializedParsingNode()


@dataclass
class SpecializedParsingNode(
    BaseNode[PipelineState, PipelineDeps, list[StructuredDocument]]
):
    """Route each segment to its specialized parser agent."""

    async def run(
        self, ctx: GraphRunContext[PipelineState, PipelineDeps]
    ) -> AssemblyNode:
        """Parse each segment using its classification-specific agent."""
        registry = ctx.deps.parser_registry
        parsed_trees: list[DocumentNode] = []

        for segment in ctx.state.segments:
            classification = segment.classification
            if classification not in registry:
                classification = DocumentClassification.UNKNOWN
            parser = registry[classification]

            metadata_summary = _build_metadata_summary(segment)
            result = await parser.run(
                f"Parse this document segment into a structured tree.\n\n"
                f"HTML:\n{segment.html}\n\n"
                f"Metadata:\n{metadata_summary}"
            )
            parsed_trees.append(result.output)

        ctx.state.parsed_trees = parsed_trees
        return AssemblyNode()


@dataclass
class AssemblyNode(BaseNode[PipelineState, PipelineDeps, list[StructuredDocument]]):
    """Merge parsed trees into final StructuredDocument(s)."""

    async def run(
        self, ctx: GraphRunContext[PipelineState, PipelineDeps]
    ) -> End[list[StructuredDocument]]:
        """Assemble parsed trees into final structured documents."""
        results: list[StructuredDocument] = []

        if ctx.state.num_documents_detected <= 1:
            # Single document — merge all trees under one root
            root = DocumentNode(
                node_type=NodeType.DOCUMENT,
                title=None,
                children=ctx.state.parsed_trees,
                metadata=NodeMetadata(
                    page_start=_min_page(ctx.state.segments),
                    page_end=_max_page(ctx.state.segments),
                ),
            )
            classification = (
                ctx.state.segments[0].classification
                if ctx.state.segments
                else DocumentClassification.UNKNOWN
            )
            results.append(
                StructuredDocument(
                    root=root,
                    classification=classification,
                    source_filename=ctx.state.ocr_document.source_filename,
                    num_pages=_max_page(ctx.state.segments),
                )
            )
        else:
            # Multi-document — group by is_separate_document boundaries
            current_trees: list[DocumentNode] = []
            current_segments: list[DocumentSegment] = []

            for segment, tree in zip(
                ctx.state.segments, ctx.state.parsed_trees, strict=True
            ):
                if segment.is_separate_document and current_trees:
                    results.append(
                        _assemble_single(current_trees, current_segments, ctx)
                    )
                    current_trees = []
                    current_segments = []
                current_trees.append(tree)
                current_segments.append(segment)

            if current_trees:
                results.append(_assemble_single(current_trees, current_segments, ctx))

        ctx.state.results = results
        return End(results)


# --- Helpers ---


def _assemble_single(
    trees: list[DocumentNode],
    segments: list[DocumentSegment],
    ctx: GraphRunContext[PipelineState, PipelineDeps],
) -> StructuredDocument:
    root = DocumentNode(
        node_type=NodeType.DOCUMENT,
        children=trees,
        metadata=NodeMetadata(
            page_start=_min_page(segments),
            page_end=_max_page(segments),
        ),
    )
    classification = (
        segments[0].classification if segments else DocumentClassification.UNKNOWN
    )
    return StructuredDocument(
        root=root,
        classification=classification,
        source_filename=ctx.state.ocr_document.source_filename,
        num_pages=_max_page(segments),
    )


def _min_page(segments: list[DocumentSegment]) -> int | None:
    pages = [s.page_start for s in segments if s.page_start is not None]
    return min(pages) if pages else None


def _max_page(segments: list[DocumentSegment]) -> int | None:
    pages = [s.page_end for s in segments if s.page_end is not None]
    return max(pages) if pages else None


def _rule_based_segmentation(
    elements: list[ParsedElement],
) -> list[DocumentSegment]:
    """Split on H1 boundaries as a simple rule-based pre-segmentation."""
    if not elements:
        return []

    segments: list[DocumentSegment] = []
    current_elements: list[ParsedElement] = []

    for elem in elements:
        if elem.tag == "h1" and current_elements:
            segments.append(_elements_to_segment(current_elements))
            current_elements = []
        current_elements.append(elem)

    if current_elements:
        segments.append(_elements_to_segment(current_elements))

    return segments


def _elements_to_segment(elements: list[ParsedElement]) -> DocumentSegment:
    """Convert a list of ParsedElements into a DocumentSegment."""
    html_parts = [e.html for e in elements]
    metadata_entries: dict[int, ElementMetadata] = {}
    for e in elements:
        if e.data_idx is not None and e.metadata is not None:
            metadata_entries[e.data_idx] = e.metadata

    pages = [e.metadata.page_number for e in elements if e.metadata is not None]
    label = (
        elements[0].text_content[:80]
        if elements and elements[0].text_content
        else "Untitled"
    )

    return DocumentSegment(
        label=label,
        html="\n".join(html_parts),
        element_metadata=ElementMetadataMap(metadata_entries),
        page_start=min(pages) if pages else None,
        page_end=max(pages) if pages else None,
    )


def _build_elements_summary(elements: list[ParsedElement]) -> str:
    """Build a text summary of elements for the segmentation agent."""
    lines: list[str] = []
    for e in elements:
        page = e.metadata.page_number if e.metadata else "?"
        lines.append(
            f"[page {page}] <{e.tag}> idx={e.data_idx}: {e.text_content[:120]}"
        )
    return "\n".join(lines)


def _build_metadata_summary(segment: DocumentSegment) -> str:
    """Build a text summary of metadata for parser agents."""
    lines: list[str] = []
    for idx, meta in sorted(segment.element_metadata.items()):
        flags = []
        if meta.is_bold:
            flags.append("bold")
        if meta.is_italic:
            flags.append("italic")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"idx={idx}: page {meta.page_number}, conf={meta.confidence:.2f}{flag_str}"
        )
    return "\n".join(lines)
