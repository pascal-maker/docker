from __future__ import annotations

from pydantic_ai import Agent

from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import get_prompt, get_prompt_config
from document_structuring_agent.models.segmentation import SegmentationResult


def create_segmentation_agent() -> Agent[None, SegmentationResult]:
    """Create an LLM agent for document segmentation."""
    config = get_prompt_config("segmentation-agent")
    model = config.model or DEFAULT_MODEL
    instructions = get_prompt("segmentation-agent")

    return Agent(
        model,
        output_type=SegmentationResult,
        instructions=instructions,
    )
