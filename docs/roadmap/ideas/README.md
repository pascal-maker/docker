---
title: Ideas and roadmap
---

# Ideas and roadmap

Design notes, future work, and deployment roadmap.

## Vision and design

- [Vision](vision.md) — Design ideas: collisions, opaque A2A, server-side orchestrator, modes (auto / ask / plan), remote state, tool calling vs DSL, CFG-constrained output.
- [Validation feedback](validation-feedback.md) — Idea: validate planner output and feed errors back to the LLM.
- [Handoff prompts](handoff-prompts.md) — Handoff prompts for the planning agent; custom MCP bridge prompt.
- [Extensible codemods](extensible-codemods.md) — Paths (on-the-fly vs RAG), iterative generation loop, prior art (Codemod.com), embedding for RAG.
- [Go-to-market strategy](go-to-market-strategy.md) — Early GTM framing across PLG and SLG.

## Evaluation

- [Benchmarking](benchmarking.md) — SWE-CI benchmark for measuring code maintenance quality once codemods are ready.

## Roadmap and deployment

- [Roadmap — generated codemod refactoring](../generated-codemod-refactoring.md) — Exploration: LLM-generated codemods for migrations.
- [Deployment — Google Marketplace](../deployment/google-market-place.md) — Roadmap: list on Google Cloud AI Agent Marketplace; checklist.
