"""Seed initial prompts into Langfuse from the prompts/ directory.

Usage:
    uv run python scripts/seed_prompts.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_CONFIGS: dict[str, dict] = {
    "segmentation-agent": {"model": "anthropic:claude-sonnet-4-6", "temperature": 0},
    "classification-agent": {"model": "anthropic:claude-sonnet-4-6", "temperature": 0},
    "parser-generic": {"model": "anthropic:claude-sonnet-4-6", "temperature": 0},
    "parser-letter": {"model": "anthropic:claude-sonnet-4-6", "temperature": 0},
    "parser-legal-schedule": {"model": "anthropic:claude-sonnet-4-6", "temperature": 0},
}


def seed() -> None:
    langfuse = get_client()

    for txt_file in sorted(PROMPTS_DIR.glob("*.txt")):
        name = txt_file.stem
        prompt_text = txt_file.read_text().strip()
        config = PROMPT_CONFIGS.get(name, {})

        langfuse.create_prompt(
            name=name,
            type="text",
            prompt=prompt_text,
            config=config,
            labels=["production"],
        )
        print(f"  Seeded prompt: {name}")

    langfuse.flush()
    print("Done.")


if __name__ == "__main__":
    seed()
