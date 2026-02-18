"""Seed initial prompts into Langfuse from the prompts/ directory.

Usage:
    uv run python scripts/seed_prompts.py
"""

from __future__ import annotations

from pathlib import Path

from document_structuring_agent.models.prompt_config import PromptConfig

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_CONFIGS: dict[str, PromptConfig] = {
    "segmentation-agent": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
    "classification-agent": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
    "parser-generic": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
    "parser-letter": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
    "parser-legal-schedule": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
    "parser-invoice": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
    "tree-agent": PromptConfig(
        model="anthropic:claude-sonnet-4-6", temperature=0, max_tokens=60000
    ),
}


def seed() -> None:
    """Seed all prompt templates from the prompts/ directory into Langfuse."""
    from dotenv import load_dotenv

    load_dotenv()

    from langfuse import get_client

    langfuse = get_client()

    for txt_file in sorted(PROMPTS_DIR.glob("*.txt")):
        name = txt_file.stem
        prompt_text = txt_file.read_text().strip()
        config = PROMPT_CONFIGS.get(name, PromptConfig())

        langfuse.create_prompt(
            name=name,
            type="text",
            prompt=prompt_text,
            config=config.model_dump(exclude_none=True),
            labels=["production"],
        )
        print(f"  Seeded prompt: {name}")

    langfuse.flush()
    print("Done.")


if __name__ == "__main__":
    seed()
