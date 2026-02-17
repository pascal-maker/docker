"""API route definitions."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile  # noqa: TC002
from fastapi.responses import JSONResponse

from api.jobs import JobStatus, create_job, get_job, run_pipeline_job

router = APIRouter(prefix="/api")


@router.post("/process", status_code=202)
async def process(file: UploadFile) -> JSONResponse:
    """Accept a PDF upload, start pipeline processing, return a job ID."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    pdf_bytes = await file.read()
    job = create_job()
    asyncio.create_task(  # noqa: RUF006
        run_pipeline_job(job, pdf_bytes, file.filename or "upload.pdf")
    )
    return JSONResponse({"job_id": job.id}, status_code=202)


@router.get("/jobs/{job_id}")
async def job_status(job_id: str) -> JSONResponse:
    """Return the current state of a job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    payload: dict[str, Any] = {
        "job_id": job.id,
        "status": job.status,
        "stage": job.stage,
    }
    if job.status == JobStatus.DONE:
        payload["result"] = job.result
    if job.status == JobStatus.ERROR:
        payload["error"] = job.error
    return JSONResponse(payload)
