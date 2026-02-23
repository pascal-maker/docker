# Refactoring

Can use a linter and typechecker after refactor.
Other checks possible too.

# Problems

Name collisions, e.g., rename foobar to main: cursor sees the collision but still performs the rename -> our agent can flag this before transform done (agent-as-a-service!) and ask explicit user approval.
Don't know you implement that with A2A though, but I'm sure it goes beyond MCP.

# Hiding what the remote refactor agent can't do (A2A)

When using our remote agent we'd prefer not to advertise the specific refactor operations it supports (so users don't see "it only does rename"). MCP being in beta is fine to mention.

**Who instructs specific refactor operations?** The **client** does. The A2A server only **executes**: it receives the message body (e.g. JSON), parses it, and runs the one implemented flow (rename). The server does not run an LLM to interpret "rename foo to bar" — it expects structured input (rename params as JSON). So whoever sends the `message/send` payload is instructing the refactor; that's the client (or the bridge/orchestrator that talks to the A2A agent). The server advertises what it accepts via the **Agent Card** (`.well-known/agent-card.json`): today it lists a skill `rename_symbol` with a full description of the JSON shape and examples. So the **server** is what currently *exposes* the capability list (via the card); the **client** is what *sends* the concrete instruction.

**How to hide:**
- **Server:** Make the Agent Card and skills generic. For example: one skill with id `refactor` (or `code_edit`), name "Refactor code", and a high-level description that does *not* enumerate operations or the exact JSON schema ("Submit a refactoring request; the agent applies supported transformations."). Optionally accept a wrapper like `{"request_type": "rename", "params": {...}}` so we can add more types later; for now only handle `request_type === "rename"`. For unsupported requests, return a generic "This refactoring is not supported" without listing what *is* supported.
- **Client:** If our client (or the bridge that invokes the agent) exposes tools to the user, don't expose a per-operation list ("rename_symbol", "extract_function", …). Expose a single "Refactor" / "Edit code" entry point that maps user intent to the one supported operation (rename) when appropriate.

# Server-side orchestrator: client sends context, server turns it into ops (confidential)

One potential design: the **coding agent (client)** sends very detailed but **non-confidential** context to the A2A agent (e.g. refactor intent, file paths, symbol names, structural hints — no secrets). The **A2A server** hosts an **orchestrator** that uses a local model (Llama or similar) to turn that refactor requirement into a structured plan — e.g. CFG/DSL or a sequence of primitive ops. We then **deterministically** execute each operation. The client never sees the internal ops or the technology; the implementation stays confidential on the server.

The orchestrator can do more than just "intent → ops": it can **inspect** intermediate state (e.g. name collisions that would arise from a particular rename), and **ask the client** for approval, extra input, or abort — without revealing *how* we detected the collision or what our op list is. So the client gets a high-level "Name collision: … Confirm? (yes/no)" (or similar) and replies; the server continues or rolls back. All orchestration, CFG/DSL, and execution details stay server-side. This might be a richer view of the A2A agent than "dumb executor that parses JSON" — the agent becomes a refactor service with an intelligent, confidential backend.

## Modes like Cursor / Claude Code: auto, ask, plan

Same idea as Cursor and Claude Code: expose **modes** so the user (or the coding agent) can choose how much agency to give.

- **Auto** — Do what the agent thinks is best. No prompts. E.g. rename would cause a collision → orchestrator picks a better name (e.g. disambiguate, suffix) and applies it. Best for low-risk, high-trust or batch cleanup.
- **Ask (interactive refactor)** — Pause for feedback. Collision? "Name X already exists here. Proceed / pick another name / abort." Multi-step refactor? "I'll do A then B. Continue?" User or client confirms or corrects. Full interactive refactor in the loop.
- **Plan** — Don't apply yet; **upgrade your codebase design**. Orchestrator produces a refactor *plan*: "Rename these 3 symbols, move this class, extract these functions." User reviews the plan; then they run it (or run parts of it) in auto or ask mode. "Plan" is the architectural level: improve structure, naming, boundaries — then execute when ready.

Realistically how good might this get? With a solid AST engine, a small refactor DSL (or JSON-schema plan), and an orchestrator that can reason about collisions, scope, and ordering: **rename + extract + move** at project scale, with deterministic execution and optional human-in-the-loop, is already in reach. The ceiling is high if we add more primitives (inline, change signature, introduce parameter), keep the orchestrator behind a single "refactor" API, and let modes (auto / ask / plan) handle the UX. Same league as "Cursor does edits" but focused on *semantic* refactors with a confidential, server-side brain.

# Remote state

With A2A keeping the remote state up to date with the local one is crucial.
How to handle this two (one?) way sync? Which protocol? Which algorithm does Jetbrains use for their semantic AST? Is there a distributed version?
Would people allow this, having all their code? How to do securely?

# Tool calling 

Rather than letting LLM do tool calling why not let it do that programmatically, i.e., write code?
See this [post](https://www.linkedin.com/posts/niels-rogge-a3b7a3127_its-quite-funny-to-see-anthropic-realizing-activity-7429942160571064320-nzLP?utm_source=share&utm_medium=member_desktop&rcm=ACoAACOjZPYBA1SGcboKFMga2ZxguGqa3t1tj5M)

We could let the LLM write code in a refactor language? Data transform language? What's the name?

## Post

It's quite funny to see Anthropic realizing what Hugging Face already said in December 2024: having LLMs take actions by writing code is much better than writing JSON.

Anthropic released Sonnet 4.6 yesterday, and, in addition to the regular benchmark jumps, it includes a new feature: "programmatic tool calling".

The idea is that you can convert tools into Python functions that Claude can run programmatically in a container. This has 2 benefits: reduced latency (as you don't require round-trips between tool calls) and lower token consumption. You can enable it by setting the "allowed_callers" flag to any tool.

It consists of the following steps:
1. Claude writes Python code that invokes the tool as a function, potentially including multiple tool calls and pre/post-processing logic
2. Claude runs this code in a sandboxed container via code execution
3. When a tool function is called, code execution pauses, and the API returns a tool_use block
4. You provide the tool result, and code execution continues (intermediate results are not loaded into Claude's context window)
5. Once all code execution completes, Claude receives the final output and continues working on the task. 

Note that this is different from simply providing Claude with the Bash tool, something which Claude Code and Cursor use. In that case, the model calls CLI and Unix commands such as `cat` and `glob`. In that case, the entire model needs to be run in a container.

Smolagent's (December 2024): https://lnkd.in/ebqhFS8u
Guide: https://lnkd.in/eNt-J2zU
Visual taken from here: https://lnkd.in/eH8uWFvE

![](https://media.licdn.com/dms/image/v2/D4E22AQFjdPPDkHWbYQ/feedshare-shrink_800/B4EZxx1BahJ0Ag-/0/1771436251180?e=1773273600&v=beta&t=07oTN7MfDa6Hr0TxepzrjI6qYaYqsaD73To4IrykxTM)

## Possible practical implementation

- **DSL instead of tool calls:** Have the agent (or A2A) output a single chainable expression, e.g. `rename("greet", "greet_user").in_file("playground/greeter.py").then(rename("foo", "bar"))`, rather than issuing multiple MCP/A2A tool calls.
- **No Python from the model:** The "code" is a tiny, fixed-vocabulary DSL (rename, in_file, in_scope, then, etc.). We parse and interpret it; we never execute arbitrary Python or run a sandbox.
- **Executor:** A small interpreter parses the DSL string and maps each step to existing `rename_symbol` (MCP or A2A) calls. Same refactor engine; only the interface changes (one DSL string → N tool invocations).
- **Benefits:** One agent round-trip for a multi-step refactor, lower token use, no container; we control the grammar so only allowed operations exist.

## CFG-constrained output = tools as the grammar

Some LLMs can be restricted to only output strings that satisfy a **context-free grammar**. If that grammar is the grammar of our refactor DSL, then the model can only emit valid tool/code expressions — no malformed JSON, no stray prose. Parse once, execute the resulting "program" of refactor steps.

**Open question: how big a refactor can we express in one shot?** The DSL could support not just linear chains but composite operations (e.g. parallel or ordered batches), so a single expression might describe a large, structured refactor. Example shape:

```text
code.rename(x -> y).parallelOperator([unroll_func(z), move_class(c), ...]).then(rename(a -> b)).in_scope("src/")...
```

Here `parallelOperator` takes a list of independent refactor ops that the executor can run in parallel (or in dependency order); `then` sequences steps; `in_scope` scopes subsequent ops. The grammar stays context-free and fixed-vocabulary, but one expression can describe a sizable refactor. Limits depend on model context, decoder support for the grammar, and how rich we make the DSL (branching, conditionals, iteration).

### How this works with Anthropic (no custom CFG)

Anthropic does **not** accept a custom CFG (e.g. BNF/EBNF). The API only supports **JSON Schema** for structured output: you pass `output_config.format` with `type: "json_schema"` and a `schema` object. Under the hood they compile that schema into a grammar and use constrained decoding so the model only emits valid JSON for that schema — but the *input* we control is always a JSON schema, not an arbitrary grammar.

**Practical approach:** Encode the refactor DSL as a **JSON structure** and give Anthropic that JSON schema. The model then outputs valid JSON that conforms to the schema; we parse that JSON into our DSL AST and execute it. So the "grammar" is effectively "all JSON documents valid for this schema", and we design the schema to be the serialization of our DSL (e.g. `{"op": "rename", "from": "x", "to": "y", "then": {...}}` or `{"steps": [{"op": "rename", ...}, {"op": "parallel", "ops": [...]}]}`). No raw DSL string like `code.rename(x->y)...` — we get JSON that *represents* the same intent.

**Limitations (Anthropic structured-output docs):** Recursive schemas are not supported, and schema complexity is capped. So we likely need a **fixed-depth or linearized** encoding (e.g. a flat or shallow list of steps, or a small fixed number of nesting levels for `parallel`/`then`) rather than unbounded recursion. String `pattern` (regex) is supported for individual string fields but cannot express full CFG (e.g. balanced parens), so we cannot constrain a single free-form DSL string. Summary: custom CFG = no; JSON schema that encodes our DSL = yes; design the schema to mirror the DSL and map JSON → executor.

**OpenAI:** Same story — the API only supports **JSON Schema** for structured output (`response_format: { type: "json_schema", schema: ... }`). No custom CFG/BNF. So for both Anthropic and OpenAI we use the JSON-encoding approach above.

**Where custom CFG *is* supported:** Local / open-source inference stacks. **llama.cpp** supports grammar-constrained decoding via **GBNF** (GGML BNF): you pass a grammar string (EBNF-like), and generation is constrained to that grammar. Python: `llama-cpp-python` exposes `LlamaGrammar.from_string(grammar_text)` and you call the model with `grammar=grammar`. So for a true “DSL string as CFG” (e.g. `code.rename(x->y).parallelOperator([...])...`) you’d need a model running through llama.cpp (or similar) with a GBNF grammar for your refactor DSL. Hugging Face Transformers is also adding CFG-constrained decoding (EBNF, compatible with llama.cpp grammars).