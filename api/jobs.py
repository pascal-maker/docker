"""In-memory job store and background pipeline task runner."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from document_structuring_agent.pipeline.graph import process_document
from document_structuring_agent.preprocessing.ocr import pdf_to_ocr_document
from document_structuring_agent.tree_agent import run_tree_agent


class JobStatus(StrEnum):
    """Pipeline job lifecycle states."""

    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class ProcessingMode(StrEnum):
    """Which processing approach to use."""

    PIPELINE = "pipeline"
    AGENT = "agent"


@dataclass
class Job:
    """A single processing job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    stage: str = "queued"
    result: list[dict[str, Any]] | None = None
    error: str | None = None
    mode: ProcessingMode = ProcessingMode.PIPELINE


_jobs: dict[str, Job] = {}


def create_job(mode: ProcessingMode = ProcessingMode.PIPELINE) -> Job:
    """Create and register a new job."""
    job = Job(mode=mode)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    """Look up a job by ID."""
    return _jobs.get(job_id)


async def run_pipeline_job(job: Job, pdf_bytes: bytes, filename: str) -> None:
    """Background task: write temp PDF, run pipeline, update job state."""
    job.status = JobStatus.PROCESSING
    job.stage = "converting pdf"

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        # pdf_to_ocr_document is synchronous (Docling); run in thread to avoid
        # blocking the event loop during OCR conversion.
        ocr_doc = await asyncio.to_thread(pdf_to_ocr_document, tmp_path)
        ocr_doc.source_filename = filename

        if job.mode == ProcessingMode.AGENT:
            job.stage = "running tree agent"
            result = await run_tree_agent(ocr_doc)
            job.result = [result.model_dump(mode="json")]
        else:
            job.stage = "running pipeline"
            results = await process_document(ocr_doc)
            job.result = [r.model_dump(mode="json") for r in results]

        job.status = JobStatus.DONE
        job.stage = "done"
    except Exception as exc:
        job.status = JobStatus.ERROR
        job.stage = "error"
        job.error = str(exc)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
