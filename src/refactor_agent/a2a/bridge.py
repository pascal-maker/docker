"""Bridge-compatible request handler: allows client-provided task_id for new tasks.

The GongRzhe A2A-MCP-Server sends params.id (task_id) on the initial message/send
so it can later call get_task_result with that id. The default A2A handler raises
"Task was specified but does not exist" when task_id is set but the task is new.
This subclass allows that case and creates the task under the client's id.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from a2a.server.context import ServerCallContext  # noqa: TC002 — used at runtime
from a2a.server.request_handlers.default_request_handler import (
    DefaultRequestHandler,
)
from a2a.server.tasks import ResultAggregator, TaskManager
from a2a.types import (  # noqa: TC002 — used at runtime
    InvalidParamsError,
    MessageSendParams,
    TaskState,
)
from a2a.utils.errors import ServerError

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

TERMINAL_TASK_STATES = {
    TaskState.completed,
    TaskState.canceled,
    TaskState.failed,
    TaskState.rejected,
}


class BridgeCompatibleRequestHandler(DefaultRequestHandler):
    """Allows message/send with client-provided task_id for new tasks (no raise)."""

    async def _setup_message_execution(
        self,
        params: MessageSendParams,
        context: ServerCallContext | None = None,
    ) -> tuple[TaskManager, str, EventQueue, ResultAggregator, asyncio.Task[object]]:
        """Like default but do not raise when task_id is set and task is new."""
        task_manager = TaskManager(
            task_id=params.message.task_id,
            context_id=params.message.context_id,
            task_store=self.task_store,
            initial_message=params.message,
            context=context,
        )
        task = await task_manager.get_task()

        if task:
            if task.status.state in TERMINAL_TASK_STATES:
                raise ServerError(
                    error=InvalidParamsError(
                        message=(
                            f"Task {task.id} is in terminal state: "
                            f"{task.status.state.value}"
                        )
                    )
                )
            task = task_manager.update_with_message(params.message, task)
        # Else: task is None. Default handler raises when params.message.task_id
        # is set; we allow it so the bridge's id is used for the new task.

        request_context = await self._request_context_builder.build(
            params=params,
            task_id=task.id if task else params.message.task_id,
            context_id=params.message.context_id,
            task=task,
            context=context,
        )

        task_id_val = request_context.task_id
        if task_id_val is None:
            raise RuntimeError("task_id missing after request context build")
        task_id = task_id_val

        if (
            self._push_config_store
            and params.configuration
            and params.configuration.push_notification_config
        ):
            await self._push_config_store.set_info(
                task_id, params.configuration.push_notification_config
            )

        queue = await self._queue_manager.create_or_tap(task_id)
        result_aggregator = ResultAggregator(task_manager)
        producer_task = asyncio.create_task(
            self._run_event_stream(request_context, queue)
        )
        await self._register_producer(task_id, producer_task)

        return task_manager, task_id, queue, result_aggregator, producer_task
