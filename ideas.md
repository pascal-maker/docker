Might make sense to have an orchestrator agent that must call the segment
agent first and thereafter cannot call it anymore?


Very good plan

Remarks:
* Always put cli / main files into a separate root folder /scripts and keep /scr a pure library
* Sometimes a single file might contain multiple documents, take for example a scanned in document where two contracts where combined. Whether you handle through the segment subagent or something else, this is important to know and take into account.


Azure OCR, and most other OCR servicces, don't just output markdown, they provide some initial structure you should use -- especially for the tables -- you can find the documentation [here](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/analyze-document-response?view=doc-intel-4.0.0).

For this proof-of-concept you may consult this summary, note that the input the structuring agent will receive is basic HTML that is equivalent to the markdown I mentioned:

## Azure Document Intelligence OCR Output Format (Simplified for PoC)

Azure Doc Intelligence (and similar OCR services) don't just return raw markdown —
they return **structured HTML with per-element metadata**.

### HTML Structure

- **Headings**: only `<h1>` (title) and `<h2>` (subtitle) — OCR does **not** provide deeper heading levels. All further hierarchy (sections, subsections, etc.) must be inferred by the structuring agent. **Important:** OCR heading classification is unreliable — titles may be missed entirely, short sentences may be misclassified as headings, and depth may be wrong. Treat OCR headings as hints, not ground truth.
- **Body text / footnotes**: `<p>`
- **Tables**: `<table>` with `<tr>`, `<th>`, `<td>`, including `rowspan`/`colspan`
- **Lists**: `<ul>`, `<ol>`, `<li>`
- Every top-level element has a `data-idx="N"` attribute linking it to metadata

```html
<h1 data-idx="0">Credit Agreement</h1>
<p data-idx="1">This agreement is entered into as of January 1, 2024...</p>
<h2 data-idx="2">Article I — Definitions</h2>
<p data-idx="3">"Affiliate" means any Person that directly controls...</p>
<table data-idx="4">
  <tr><th>Term</th><th>Definition</th></tr>
  <tr><td>Borrower</td><td>XYZ Corp</td></tr>
</table>
```

### Per-Element Metadata

Each `data-idx` maps to a metadata record with: `page_number`, `confidence` (0–1), bounding box (`left`, `top`, `width`, `height` on a 0–1000 grid), styling flags (`is_bold`, `is_italic`, `font_family`), and `is_page_header` (repeated headers like "CONFIDENTIAL").

### Key Takeaways for the PoC

1. **Don't re-detect what OCR already provides.** Tables, headings, and lists are already tagged — parse them from the HTML.
2. **Page boundaries** come from metadata (`page_number`), not from the HTML itself. Some services also insert `<!-- PageBreak -->` markers.
3. **Page headers are flagged** (`is_page_header`) — typically skip these.
4. For the PoC, assume metadata is available as a list of dicts keyed by `data-idx`.



---

# Refactoring

Can use a linter and typechecker after refactor.
Other checks possible too.