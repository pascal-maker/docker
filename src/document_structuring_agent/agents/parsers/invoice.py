from __future__ import annotations

from pydantic_ai import Agent

from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import get_prompt, get_prompt_config
from document_structuring_agent.models.nodes import DocumentNode


def create_invoice_parser_agent() -> Agent[None, DocumentNode]:
    """Create a specialized parser agent for invoice documents."""
    config = get_prompt_config("parser-invoice")
    model = config.model or DEFAULT_MODEL
    instructions = get_prompt("parser-invoice")

    return Agent(
        model,
        output_type=DocumentNode,
        instructions=instructions,
    )
