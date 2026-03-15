---
title: Benchmarking
---

# Benchmarking

## SWE-CI

Once the agent has codemods and automated refactor improvements, evaluate it against the [SWE-CI benchmark](https://swe-ci.com), which allegedly measures code maintenance quality.

This would give us an objective signal on whether the agent meaningfully improves real-world code maintenance tasks.

## Related Papers

### An Empirical Study on the Code Refactoring Capability of Large Language Models (2024)

[arxiv:2411.02320](https://arxiv.org/abs/2411.02320) — Cordeiro, Noei, Zou

Benchmarks StarCoder2 on 30 open-source Java projects across three dimensions: code quality improvements, refactoring type effectiveness, and prompting strategies (one-shot, chain-of-thought). Key findings:

- Reduced code smells by >20%, especially systematic issues (lengthy statements, magic numbers)
- Human developers outperformed the model on complex, context-dependent refactorings
- One-shot prompting improved unit test pass rates by ~6%
- Generating multiple candidates per input improved pass rates by ~28.8%

**Relevance:** Low. Pure text-in/text-out LLM benchmark with no tool-based or AST-driven approach. Does not discuss codemods, structured transformations, or anything like ts-morph. RMiner 3.0 is used only to classify refactorings after the fact, not to apply them.
