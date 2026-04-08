# Ideas & Go-to-Market Strategy

## Two GTM Tracks: Sales-Led Growth (SLG) + Product-Led Growth (PLG)

### Core Pain

Teams are sitting on massive codebases that can't be refactored "in one go."
Upgrades (e.g. new React patterns, FastAPI migrations) demand enormous
iteration effort, and you hit the ceiling fast when relying purely on "fancy
agents."

---

## MVP Proposal

**Simple product surface, strong tech underneath.**

- Use LLM calls + tool calls to iteratively plan toward a well-defined end
  state.
- Not one mega-refactor, but **pattern-by-pattern codemods**: for each known
  pattern, write a transformer that automatically rewrites the code
  deterministically where possible.
- Optional: **VS Code extension** as a UX layer (PLG entry point).
- **CI/CD integration** (e.g. Aikido-style checks) to safely validate changes
  before they land.

---

## Distribution

### PLG (Product-Led Growth)

- Self-serve onboarding
- A compelling "wow" demo
- Launch traction via Hacker News

### SLG (Sales-Led Growth)

- Target larger teams with real "large codebase" pain
- Faster adoption cycle + budget availability

---

## North Star

Build a tool that **reliably migrates large codebases through small, repeatable
transformations** — replacing agent chaos with structured, auditable codemods.
