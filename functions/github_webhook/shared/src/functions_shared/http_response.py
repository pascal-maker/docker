"""HTTP response model and decorator for Flask/functions_framework."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec

from pydantic import BaseModel, RootModel

P = ParamSpec("P")


class HttpHeaders(RootModel[dict[str, str]]):
    """HTTP response headers as dict wrapper."""

    root: dict[str, str] = {}


class HttpResponse(BaseModel):
    """HTTP response for Cloud Functions. Use @http_handler to convert to Flask tuple."""

    body: str
    status: int
    headers: HttpHeaders = HttpHeaders()

    def to_flask_tuple(self):
        """Convert to (body, status, headers) for Flask/functions_framework."""
        return (self.body, self.status, self.headers.root)


def http_handler(handler: Callable[P, HttpResponse]):
    """Decorator that wraps a handler returning HttpResponse and converts to Flask tuple."""

    def wrapper(*args: P.args, **kwargs: P.kwargs):
        response = handler(*args, **kwargs)
        return response.to_flask_tuple()

    return wrapper  # type: ignore[return-value]
