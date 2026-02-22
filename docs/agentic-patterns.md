---
title: Agentic patterns
---

# Agentic patterns

This doc gives a short overview of **agentic patterns**: reusable workflows for AI agents (planning, tool use, refinement). It points to external references and how they relate to this project.

## What are agentic patterns?

Agentic patterns are structured workflows that break complex agent behaviour into clear stages, state, tool use, and optional refinement — instead of ad-hoc single prompts. They improve reliability, debuggability, and reusability.

**Reference:** [What Are Agent Patterns? — Agent Patterns](https://agent-patterns.readthedocs.io/en/latest/concepts/what-are-patterns.html) — definitions, comparison with ad-hoc approaches, and when to use patterns vs simple prompts.

## Common pattern categories

| Category            | Examples                    | Use when |
|---------------------|-----------------------------|----------|
| **Tool-using**      | ReAct, REWOO, LLM Compiler  | Search, APIs, external data, multi-step tool calls |
| **Refinement**      | Reflection, Reflexion, LATS | Output quality is critical (writing, code, design) |
| **Planning**        | Plan & Solve, Self-Discovery| Multi-step tasks, strategic decomposition |
| **Multi-perspective** | STORM                      | Research, synthesis from multiple viewpoints |

Patterns are often combined (e.g. plan then execute, or tool use then structured output).

## Patterns used in this project

- **Orchestrator:** Single agent with tools (rename, move_symbol, find_references, etc.). User message → tool loop → final answer. Conceptually **ReAct-style**: reason, act with tools, observe, repeat.
- **Planner (refactor schedule):** Specialist agent with **read-only** tools and **structured output** (`RefactorSchedule`). Exploration via tools, then one validated plan — a **plan-then-execute** split: planner produces the schedule, executor runs it. See [Refactor schedule](refactor-schedule/README.md) and the implementation plan.
- **Optional refinement:** Executor validates the schedule (paths, `depends_on`, no cycles); validation errors can be fed back to the planner for a **critic/refine** loop (post-MVP).

## LLM Compiler and the refactor schedule

The refactor schedule is a close fit for the **LLM Compiler** pattern: a DAG of operations with explicit dependencies, executed in topological order (and eventually in parallel where safe).

**Reference:** [LLM Compiler Agent Pattern — Agent Patterns](https://agent-patterns.readthedocs.io/en/latest/patterns/llm-compiler.html)

| LLM Compiler concept        | Refactor schedule equivalent                          |
|----------------------------|--------------------------------------------------------|
| Planner produces DAG       | Planner produces `RefactorSchedule` (goal + operations) |
| Nodes = tool calls + `depends_on` | Ops = rename / move_symbol / … with optional `depends_on` |
| Topological execution      | Executor topo-sorts by `depends_on`, runs in order     |
| Parallel ready nodes       | MVP: sequential only; later: waves / parallel execution |

Today the executor runs steps **sequentially** in topo order (no parallelism). The [refactor-schedule README](refactor-schedule/README.md) leaves **DAG enrichment** (affected spans, conflict graph) and **waves / parallel execution** for later (steps 8–9). Adopting the LLM Compiler framing makes that path explicit: same DAG model, add parallel execution of independent ops when the engine supports it.

## Further reading

- **Agent Patterns (readthedocs):** [Agent Patterns](https://agent-patterns.readthedocs.io/) — ReAct, Reflection, Plan & Solve, REWOO, [LLM Compiler](https://agent-patterns.readthedocs.io/en/latest/patterns/llm-compiler.html), and others with APIs and examples.
- **Plan-and-execute:** [LangChain Plan-and-Execute](https://blog.langchain.com/plan-and-execute-agents), [LangGraph Plan-and-Execute](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/) — planner produces a plan, executor runs steps.
- **Orchestrator + sub-agent:** [Microsoft Copilot — Orchestrator and sub-agent](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/architecture/multi-agent-orchestrator-sub-agent) — when to delegate to specialist agents.
- **Pydantic AI:** [Output](https://ai.pydantic.dev/output), [Tools](https://ai.pydantic.dev/tools) — structured output and tool use (used by our orchestrator and planner).
