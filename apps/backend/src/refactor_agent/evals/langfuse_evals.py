"""Reusable Langfuse dataset and experiment helpers.

Use for triage validation, router evals, and future evaluation workflows.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from langfuse import get_client


class DatasetItem(BaseModel):
    """Single dataset item for create_or_update_dataset."""

    input: dict[str, object]
    expected_output: dict[str, object] | None = None
    metadata: dict[str, object] | None = None


class ExperimentConfig(BaseModel):
    """Optional experiment configuration."""

    evaluators: list[Callable[..., Any]] = Field(default_factory=list)
    run_evaluators: list[Callable[..., Any]] = Field(default_factory=list)
    max_concurrency: int = 5
    metadata: dict[str, object] | None = None

    model_config = {"arbitrary_types_allowed": True}


def create_or_update_dataset(
    name: str,
    description: str,
    items: list[DatasetItem],
) -> None:
    """Create or update a Langfuse dataset with items.

    If the dataset does not exist, it is created. Items are appended.
    For full replace, delete the dataset in Langfuse UI first, then re-run.
    """
    langfuse = get_client()
    with contextlib.suppress(Exception):  # Dataset exists; continue to add items
        langfuse.create_dataset(name=name, description=description)
    for item in items:
        langfuse.create_dataset_item(
            dataset_name=name,
            input=item.input,
            expected_output=item.expected_output,
            metadata=item.metadata,
        )
    langfuse.flush()


def run_experiment_on_dataset(
    dataset_name: str,
    task: Callable[..., object],
    name: str,
    description: str,
    config: ExperimentConfig | None = None,
) -> object:
    """Run an experiment on a Langfuse dataset.

    Fetches the dataset by name and runs the task on each item. The task receives
    item (with .input, .expected_output, .metadata) and **kwargs. Task may be sync
    or async. Returns ExperimentResult with .format() for display.
    """
    cfg = config or ExperimentConfig()
    langfuse = get_client()
    dataset = langfuse.get_dataset(dataset_name)
    opts: dict[str, Any] = {
        "evaluators": cfg.evaluators,
        "run_evaluators": cfg.run_evaluators,
        "max_concurrency": cfg.max_concurrency,
    }
    if cfg.metadata is not None:
        opts["metadata"] = cfg.metadata
    return dataset.run_experiment(
        name=name,
        description=description,
        task=task,
        **opts,
    )
