"""Reusable base for engines that delegate to a child process via JSON-RPC."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class SubprocessError(Exception):
    """Raised when the subprocess bridge returns an error or crashes."""


class SubprocessEngine(ABC):
    """Base for engines that delegate to a child process via JSON-RPC.

    Communicates over newline-delimited JSON on stdin/stdout.
    Request:  ``{"id": N, "method": "...", "params": {...}}``
    Response: ``{"id": N, "result": ...}`` or ``{"id": N, "error": "..."}``
    """

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._lock = asyncio.Lock()

    @abstractmethod
    def _command(self) -> list[str]:
        """Return the command + args to start the bridge process."""

    async def __aenter__(self) -> SubprocessEngine:
        """Start the bridge child process."""
        cmd = self._command()
        logger.debug("Starting subprocess: %s", cmd)
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Terminate the bridge child process."""
        proc = self._process
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except (TimeoutError, ProcessLookupError):
            proc.kill()
        finally:
            self._process = None

    async def _call(self, method: str, params: dict[str, Any]) -> Any:  # noqa: ANN401 — JSON-RPC result type varies per method
        """Send a JSON-RPC request and return the result.

        Raises:
            SubprocessError: If the bridge returns an error or the process
                has terminated unexpectedly.
        """
        proc = self._process
        if proc is None or proc.stdin is None or proc.stdout is None:
            msg = "Subprocess not started; use 'async with' context manager"
            raise SubprocessError(msg)

        async with self._lock:
            self._request_id += 1
            request_id = self._request_id

            payload = json.dumps(
                {"id": request_id, "method": method, "params": params},
            )
            proc.stdin.write(payload.encode() + b"\n")
            await proc.stdin.drain()

            raw_line = await proc.stdout.readline()
            if not raw_line:
                stderr_bytes = b""
                if proc.stderr is not None:
                    stderr_bytes = await proc.stderr.read()
                stderr_text = stderr_bytes.decode(errors="replace").strip()
                msg = f"Bridge process exited unexpectedly: {stderr_text}"
                raise SubprocessError(msg)

            try:
                response = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON from bridge: {raw_line!r}"
                raise SubprocessError(msg) from exc

            if response.get("id") != request_id:
                msg = (
                    f"Response id mismatch: "
                    f"expected {request_id}, got {response.get('id')}"
                )
                raise SubprocessError(msg)

            if "error" in response:
                msg = f"Bridge error: {response['error']}"
                raise SubprocessError(msg)

            return response.get("result")
