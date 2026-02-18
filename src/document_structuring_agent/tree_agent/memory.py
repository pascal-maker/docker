"""Within-session pattern memory for the tree agent.

Accumulates structural rules discovered by the agent during tree construction.
Confirmed patterns are injected into each iteration's prompt so the agent
doesn't rediscover the same rules on every loop.
"""

from __future__ import annotations

from pydantic import BaseModel, PrivateAttr


class ConfirmedPattern(BaseModel):
    """A structural rule confirmed during tree construction."""

    description: str
    example_node_id: str
    iteration_confirmed: int


class PatternMemory(BaseModel):
    """Accumulates confirmed structural patterns within a single agent session.

    Patterns are appended via record() and rendered as a compact block
    for injection into the agent's iteration prompt.
    """

    patterns: list[ConfirmedPattern] = []
    _iteration: int = PrivateAttr(default=0)

    def record(self, description: str, example_node_id: str) -> None:
        """Record a confirmed structural pattern.

        Args:
            description: Human-readable rule, e.g. 'bold h2 = section heading'.
            example_node_id: The node ID that triggered this rule.
        """
        self.patterns.append(
            ConfirmedPattern(
                description=description,
                example_node_id=example_node_id,
                iteration_confirmed=self._iteration,
            )
        )

    def advance_iteration(self) -> None:
        """Increment the current iteration counter."""
        self._iteration += 1

    @property
    def current_iteration(self) -> int:
        """Current iteration index."""
        return self._iteration

    def to_prompt_block(self) -> str:
        """Render patterns as a compact bullet list for LLM context injection."""
        if not self.patterns:
            return "(no patterns confirmed yet)"
        return "\n".join(f"- {p.description}" for p in self.patterns)
