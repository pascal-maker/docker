from __future__ import annotations

from anthropic import AsyncAnthropic
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.settings import ModelSettings

from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import get_prompt, get_prompt_config
from document_structuring_agent.models.segmentation import SegmentationResult


def create_segmentation_agent() -> Agent[None, SegmentationResult]:
    """Create an LLM agent for document segmentation."""
    config = get_prompt_config("segmentation-agent")
    model_str = config.model or DEFAULT_MODEL
    instructions = get_prompt("segmentation-agent")

    # Extract model ID from "anthropic:claude-sonnet-4-6" format
    model_id = model_str.split(":")[-1] if ":" in model_str else model_str

    model_settings = ModelSettings(max_tokens=config.max_tokens or 60000)

    # Use a custom client with timeout=None so requests exceeding 10 minutes
    # don't hit the Anthropic SDK's idle-connection drop warning.
    provider = AnthropicProvider(anthropic_client=AsyncAnthropic(timeout=None))
    model = AnthropicModel(model_id, provider=provider, settings=model_settings)

    return Agent(
        model,
        output_type=SegmentationResult,
        instructions=instructions,
    )
