from __future__ import annotations

from pydantic_ai import Agent

from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import get_prompt, get_prompt_config
from document_structuring_agent.models.classification import ClassificationResult


def create_classification_agent() -> Agent[None, ClassificationResult]:
    """Create an LLM agent for classifying document segments."""
    config = get_prompt_config("classification-agent")
    model = config.model or DEFAULT_MODEL
    instructions = get_prompt("classification-agent")

    return Agent(
        model,
        output_type=ClassificationResult,
        instructions=instructions,
    )
