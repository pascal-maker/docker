"""Cloud Function: Daily usage digest email.

HTTP-triggered by Cloud Scheduler. Queries Firestore (new users) and Cloud
Monitoring (auth/email function invocations), sends digest via Resend.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import UTC, datetime, timedelta

import functions_framework
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.types import (
    Aggregation,
    ListTimeSeriesRequest,
    TimeInterval,
)
from google.protobuf.timestamp_pb2 import Timestamp
from pydantic import BaseModel, Field

from functions_shared import HttpHeaders, HttpResponse, http_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _count_new_users(project_id: str) -> int:
    """Count users created in the last 24 hours."""
    db = firestore.Client(project=project_id)
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    query = db.collection("users").where(filter=FieldFilter("created_at", ">=", cutoff))
    return sum(1 for _ in query.stream())


def _get_request_count(
    project_id: str,
    client: MetricServiceClient,
    service_name: str,
    start_time: datetime,
    end_time: datetime,
) -> int:
    """Get request count for a Cloud Run service in the time window."""
    filter_str = (
        'metric.type="run.googleapis.com/request_count" '
        'AND resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{service_name}"'
    )
    start_ts = Timestamp()
    start_ts.FromDatetime(start_time)
    end_ts = Timestamp()
    end_ts.FromDatetime(end_time)
    interval = TimeInterval(start_time=start_ts, end_time=end_ts)
    request = ListTimeSeriesRequest(
        name=f"projects/{project_id}",
        filter=filter_str,
        interval=interval,
        aggregation=Aggregation(
            alignment_period={"seconds": 86400},
            per_series_aligner=Aggregation.Aligner.ALIGN_SUM,
        ),
    )
    total = 0
    for ts in client.list_time_series(request=request):
        for point in ts.points:
            if point.value.int64_value is not None:
                total += point.value.int64_value
    return total


class ResendEmailPayload(BaseModel):
    """Resend API email payload."""

    from_: str = Field(alias="from")
    to: list[str]
    subject: str
    html: str

    model_config = {"populate_by_name": True}


def _send_digest_email(
    admin_email: str,
    api_key: str,
    new_users: int,
    auth_callbacks: int,
    email_notifies: int,
) -> None:
    """Send digest email via Resend API."""
    from_addr = os.environ.get("FROM_EMAIL", "Refactor Agent <noreply@refactorum.com>")
    subject = (
        f"Refactor Agent - Daily digest: {new_users} new users, "
        f"{auth_callbacks} auth callbacks, {email_notifies} emails sent"
    )
    html = (
        "<p>Daily usage digest (last 24h):</p>"
        "<ul>"
        f"<li><strong>New users:</strong> {new_users}</li>"
        f"<li><strong>Auth callbacks:</strong> {auth_callbacks}</li>"
        f"<li><strong>Email notifications:</strong> {email_notifies}</li>"
        "</ul>"
    )
    payload = ResendEmailPayload(
        from_=from_addr,
        to=[admin_email],
        subject=subject,
        html=html,
    )
    body = json.dumps(payload.model_dump(by_alias=True)).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "refactor-agent-usage-digest/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            result = json.loads(raw) if raw else {}
            logger.info("Resend sent digest to=%s id=%s", admin_email, result.get("id"))
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.exception("Resend API error: %s %s", e.code, body)
        raise


@functions_framework.http
@http_handler
def usage_digest(request) -> HttpResponse:
    """HTTP handler: gather usage metrics and send digest email."""
    admin_email = os.environ.get("ADMIN_EMAIL")
    api_key = os.environ.get("RESEND_API_KEY")
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")

    logger.info(
        "usage_digest started admin=%s project=%s",
        admin_email or "(unset)",
        project_id or "(unset)",
    )

    if not admin_email or not api_key or not project_id:
        logger.error(
            "Missing config: admin=%s api_key=%s project=%s",
            bool(admin_email),
            bool(api_key),
            bool(project_id),
        )
        return HttpResponse(
            body="Missing ADMIN_EMAIL, RESEND_API_KEY, or project",
            status=500,
        )

    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=24)

    new_users = _count_new_users(project_id)

    client = MetricServiceClient()
    auth_callbacks = _get_request_count(
        project_id, client, "auth-github-callback", start_time, end_time
    )
    email_notifies = _get_request_count(
        project_id, client, "email-notify-pending-user", start_time, end_time
    )

    logger.info(
        "Sending digest: users=%s auth=%s emails=%s",
        new_users,
        auth_callbacks,
        email_notifies,
    )
    _send_digest_email(admin_email, api_key, new_users, auth_callbacks, email_notifies)

    return HttpResponse(
        body="OK",
        status=200,
        headers=HttpHeaders(root={"Content-Type": "text/plain"}),
    )
