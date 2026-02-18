from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import get_prompt, get_prompt_config
from document_structuring_agent.models.classification import ClassificationResult


def create_classification_agent() -> Agent[None, ClassificationResult]:
    """Create an LLM agent for classifying document segments."""
    config = get_prompt_config("classification-agent")
    model = config.model or DEFAULT_MODEL
    instructions = get_prompt("classification-agent")

    model_settings = None
    if config.max_tokens:
        model_settings = ModelSettings(max_tokens=config.max_tokens)

    return Agent(
        model,
        output_type=ClassificationResult,
        instructions=instructions,
        model_settings=model_settings,
    )
