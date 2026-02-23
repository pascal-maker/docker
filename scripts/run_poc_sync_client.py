"""Run POC sync client: connect to sync server, bootstrap, then sync .py files on save."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from refactor_agent.sync.client import run_sync_client_with_queue

try:
    from watchdog.events import FileModifiedEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    # Stubs when watchdog is not installed (script exits early in main() if Observer is None).
    class _StubEventHandler:
        def on_modified(self, event: object) -> None: ...

    class _StubFileEvent:
        src_path: str = ""

    Observer = None
    FileSystemEventHandler = _StubEventHandler
    FileModifiedEvent = _StubFileEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_WS_URL = os.environ.get("POC_SYNC_WS_URL", "ws://localhost:8765")


class PyFileHandler(FileSystemEventHandler):
    """On .py file modification, put path into queue for sync."""

    def __init__(
        self,
        root: Path,
        queue: asyncio.Queue[Path | None],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.root = root.resolve()
        self.queue = queue
        self.loop = loop

    def on_modified(self, event: object) -> None:
        if not isinstance(event, FileModifiedEvent):
            return
        src = getattr(event, "src_path", None)
        if not src:
            return
        path = Path(src)
        if path.suffix != ".py" or not path.is_file():
            return
        try:
            path.resolve().relative_to(self.root)
        except ValueError:
            return
        self.loop.call_soon_threadsafe(self.queue.put_nowait, path)


async def _run_client(
    ws_url: str, root: Path, path_queue: asyncio.Queue[Path | None]
) -> None:
    """Run sync client; exit when None is put in queue."""
    await run_sync_client_with_queue(ws_url, root, path_queue)


def main() -> None:
    """Run sync client with optional watchdog on-save sync."""
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    ws_url = os.environ.get("POC_SYNC_WS_URL", DEFAULT_WS_URL)

    obs_cls = Observer
    if obs_cls is None:
        logger.error("watchdog not installed; run: uv add watchdog")
        sys.exit(1)

    path_queue: asyncio.Queue[Path | None] = asyncio.Queue()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def stop() -> None:
        path_queue.put_nowait(None)

    try:
        loop.add_signal_handler(signal.SIGINT, stop)
        loop.add_signal_handler(signal.SIGTERM, stop)
    except (ValueError, OSError):
        pass

    handler = PyFileHandler(root, path_queue, loop)
    observer = obs_cls()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()

    try:
        loop.run_until_complete(_run_client(ws_url, root, path_queue))
    finally:
        observer.stop()
        observer.join()
        loop.close()


if __name__ == "__main__":
    main()
