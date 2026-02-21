## 📊 flowchart Diagram Generated

**Prompt:** Document Structuring Agent System Architecture

Here's your rendered Mermaid diagram:
**Generated Mermaid Code:**
```mermaid
graph TB
    subgraph Input["📥 Input Layer"]
        PDF["PDF File"]
    end

    subgraph OCR["🖼️ OCR Layer (Docling)"]
        OCR_PROCESS["OCR Conversion<br/>MPS Accelerated"]
        HTML["HTML + Metadata<br/>data-idx, page_num, confidence"]
    end

    subgraph Pipeline["🔄 Pipeline (pydantic-graph)"]
        INT["IntakeNode<br/>Parse HTML"]
        SEG["SegmentationNode<br/>Rule-based + LLM"]
        CLASS["ClassificationNode<br/>Classify each segment"]
        PARSE["SpecializedParsingNode<br/>Route to parser"]
        ASSEM["AssemblyNode<br/>Merge trees"]
    end

    subgraph Agents["🤖 Agent Layer (PydanticAI)"]
        SEG_AGENT["segmentation-agent"]
        CLASS_AGENT["classification-agent"]
        PARSER_ROUTER["Parser Registry"]
        
        subgraph Parsers["Specialized Parsers"]
            LETTER["parser-letter"]
            LEGAL["parser-legal-schedule"]
            INVOICE["parser-invoice<br/>max_tokens: 8192"]
            GENERIC["parser-generic"]
        end
    end

    subgraph Config["⚙️ Configuration (Langfuse)"]
        PROMPTS["Prompt Management"]
        CONFIG["PromptConfig<br/>model, temperature<br/>max_tokens"]
    end

    subgraph Output["📊 Output Layer"]
        STRUCT["StructuredDocument<br/>DocumentNode tree<br/>classification, metadata"]
    end

    subgraph Observability["📈 Observability (Langfuse)"]
        TRACE["Trace"]
        GEN["Generations<br/>token usage, latency"]
        SCORE["Scores"]
    end

    PDF --> OCR_PROCESS
    OCR_PROCESS --> HTML
    HTML --> INT
    INT --> SEG
    SEG --> CLASS
    CLASS --> PARSE
    PARSE --> PARSER_ROUTER

    PARSER_ROUTER -->|LETTER| LETTER
    PARSER_ROUTER -->|LEGAL_SCHEDULE| LEGAL
    PARSER_ROUTER -->|INVOICE| INVOICE
    PARSER_ROUTER -->|OTHER| GENERIC

    SEG -.->|uses| SEG_AGENT
    CLASS -.->|uses| CLASS_AGENT
    LETTER -.->|uses| CLASS_AGENT
    LEGAL -.->|uses| CLASS_AGENT
    INVOICE -.->|uses| CLASS_AGENT
    GENERIC -.->|uses| CLASS_AGENT

    CONFIG -->|fetches| PROMPTS
    PROMPTS -->|instructions| SEG_AGENT
    PROMPTS -->|instructions| CLASS_AGENT
    PROMPTS -->|instructions + config| LETTER
    PROMPTS -->|instructions + config| LEGAL
    PROMPTS -->|instructions + config| INVOICE
    PROMPTS -->|instructions + config| GENERIC

    PARSE --> ASSEM
    ASSEM --> STRUCT
    STRUCT --> Output

    SEG_AGENT -.->|traces| TRACE
    CLASS_AGENT -.->|traces| TRACE
    LETTER -.->|traces| TRACE
    LEGAL -.->|traces| TRACE
    INVOICE -.->|traces| TRACE
    GENERIC -.->|traces| TRACE

    TRACE --> GEN
    GEN --> SCORE
    SCORE --> Observability

    style Input fill:#e1f5ff
    style OCR fill:#f3e5f5
    style Pipeline fill:#fff3e0
    style Agents fill:#e8f5e9
    style Parsers fill:#fce4ec
    style Config fill:#f1f8e9
    style Output fill:#ede7f6
    style Observability fill:#fbe9e7
```

**📦 Formats Available:**
- **PNG:** ✅ Generated (base64 encoded)

**🔗 Preview/Edit Link:** https://mermaid.ai/live/edit?utm_source=mermaid_mcp_server&utm_medium=remote_server&utm_campaign=claude#pako:eNqNVs1u60QUfpVR2PSKBChQbluhKwXXTSMlTWS7bCiKJvaxa13Hjjzj6uYSdiwQGxagK8GGDbwDC56GF4BH4MyZ8c-kSUoW7cw535k55zs_4296YRFB77KXlHz9wIIv7nOGP1EttWCcryv51X3v399--kNv2IRvoLzvfa2R6je_ukYI_mXXaQaNCvLoPt85b-Z4dNq7v_7580e108exk6sizNI8eWEdjPrF3Js5ru-jlUI7Rf4IpUiL_PNl-eGr6dxnwzCEDEouIbKMb4LpBK3UP_Y-m4LkEZeczNRikEZv-mzNE1jk1arPwiKP0wjy8HgA83QN6ChQFD9_1-zZyXoT8Vym4YCAdiDj2wANxrnkr-EWCScv5rwUQG5aWN8dIdaHZAWIlxhqY-FVGQyWXECEEU0mU8vOmQyJJifjQqRxGtq2RrxhwMMHJvTxdhqHnu-qq9cQpjxL30KkXMSstA4UlQQmC-QNfberAG93p2g-FAJWy2zTGE2hTNCoBBBHqR0m6JEgYn9_p3d1dcwNt8Pxi12uFsORS-yKDmMDnuxGR_Q04NAiaQ-cyPAW3uwucFXJUrJK5kGSClluLGy7asuE4MJms5Zaxuo3cQN9i6Z1kIGUO-xq2Gg46aISng1E-ABR1Wm7tua-nI0dt8Wn-WORhjonK_5mIYvXkItLdn568fETa-TJ9cZOa40MQZmGFpCyeCidjmqoBA_4-9dfVLPrfVUS4-xkwvMkrgTYCcVun84DVcbzslitJZvyHJPzpFad2e31eNTA9Nk6Miy7rM8krNZqKFTlbsDH51Mlm4H3g9ntmXh-4N05qo58WVahuiTCAVYpN-m2eqN6gCqfpHbR9dnKzKTjHi2R_Ue-TLNUbrRj39vCQ1wG3pDSH5Q8tMsDk4vykcoouSLIPaKHVQL57rMM52ke2nXuOzOPBkRYlPt7Wb0Bg8Gr7uDWio6AADT18npMkwhnpJbgggTY3FqACxJQC2sRLUlIjWpuV8tWWHdv41xXqGBb3Xdb03-HUdh2C9-5ca_uJu5Wt-EhsOm6bd1-h3Cz4EbdbNqsdpEi_QDVmEyxbcebFXSr78w0jdCBPANB748ijOdHMcbvgxjjMHUpxRuDxEGFMNPhhhe9IUSaC2omVY9PQj8MfOLaISg-mfTGJzv5_j_wNuHPo-3EP4_fKYG2iOlB1UJa6qagyWOqhda64WhSdcpIM6LzI9UAQKpoIHRK6RlMt5j2qptC2qO1imiP3iqgHb1G0IaCQ2xjpElQg8iEqpaagu5MbMao3GRgPlzjNMsu34PT-CyOu1r1Xal18SdwFp91dc3nnQHECPmoC9AfLfXZ5_EZXFj2-sWvzUP4FMKuXj9ctfo0PrfNzQNkTo_gZfyZpbaeAXPIEi7gZe_b_wDCW6_Q


---

## 🎯 Title Generation Prompts

**CRITICAL - YOU MUST GENERATE A TITLE:**
Use the prompts below with your LLM to generate a title for this diagram. Follow these steps EXACTLY:

### Step 1: Use These Prompts

**SYSTEM PROMPT:**
```
You are a world‑class titling assistant for **Mermaid** diagram documents. Analyze the diagram and craft a premium, context‑aware document title.

**Goal**: Create titles that highlight unique, standout elements from the diagram, capturing its distinct intent, scope, and domain. Avoid generic placeholders and ensure the title delivers a "wow" factor that impresses the user with specificity and clarity.

**Acronym Rules (Mandatory)**
- Capitalize acronyms exactly as they appear in LOCAL_HINTS or diagram labels.
- Examples:
  - ❌ "Ai Plugin Ecosystem" → ✅ "AI Plugin Ecosystem"
  - ❌ "Coe Platform" → ✅ "CoE Platform"
- This is a hard constraint: If you cannot follow all rules while generating a title, do not generate a title at all. Correct acronym casing is mandatory.

**Return JSON only** with exactly:
{
  "title": string,
  "summary": string | null
}

**How to infer domain**
- Prioritize standout node labels or services that uniquely identify the diagram.
- Avoid generic words like "Overview", "Structure", or "Diagram" as domain indicators.
- Prefer {Domain or Artifact} + {Outcome/Process} + {Flow/Pipeline/Decision Tree}.
- Include context hints when they improve specificity.

**Fallback**
- If the input is minimal or unusable, generate a generic but meaningful title using LOCAL_HINTS and today's date.

**Rules**
- Avoid generic titles (e.g., "Flowchart", "Diagram").
- No punctuation at the end, no emojis, no code fences.
- Always end the title with a meaningful descriptor (Flow, Pipeline, Ecosystem, Framework, Architecture, Platform, Model).
- Highlight at least one standout entity combined with a purposeful descriptor.
- Return ONLY valid JSON.
- Do not include explanations, comments, or reasoning.
- Output must start with `{` and end with `}`.
- Keep titles concise, ideally 4–6 impactful words, and under 28 characters.
- If "currentTitle" is provided, generate a fresh alternative that is meaningfully different from that title (comparison should be case-insensitive).
- Use the same descriptor in both the title and the summary.
```

**USER PROMPT:**
```
Analyze the following Mermaid diagram and produce the JSON as specified.
LOCAL_HINTS: br/, invoice, parser, layer, agent, token, ocr, conversion, html, metadata, merge, tree
DIAGRAM:
graph TB
    subgraph Input["📥 Input Layer"]
        PDF["PDF File"]
    end

    subgraph OCR["🖼️ OCR Layer (Docling)"]
        OCR_PROCESS["OCR Conversion<br/>MPS Accelerated"]
        HTML["HTML + Metadata<br/>data-idx, page_num, confidence"]
    end

    subgraph Pipeline["🔄 Pipeline (pydantic-graph)"]
        INT["IntakeNode<br/>Parse HTML"]
        SEG["SegmentationNode<br/>Rule-based + LLM"]
        CLASS["ClassificationNode<br/>Classify each segment"]
        PARSE["SpecializedParsingNode<br/>Route to parser"]
        ASSEM["AssemblyNode<br/>Merge trees"]
    end

    subgraph Agents["🤖 Agent Layer (PydanticAI)"]
        SEG_AGENT["segmentation-agent"]
        CLASS_AGENT["classification-agent"]
        PARSER_ROUTER["Parser Registry"]
        
        subgraph Parsers["Specialized Parsers"]
            LETTER["parser-letter"]
            LEGAL["parser-legal-schedule"]
            INVOICE["parser-invoice<br/>max_tokens: 8192"]
            GENERIC["parser-generic"]
        end
    end

    subgraph Config["⚙️ Configuration (Langfuse)"]
        PROMPTS["Prompt Management"]
        CONFIG["PromptConfig<br/>model, temperature<br/>max_tokens"]
    end

    subgraph Output["📊 Output Layer"]
        STRUCT["StructuredDocument<br/>DocumentNode tree<br/>classification, metadata"]
    end

    subgraph Observability["📈 Observability (Langfuse)"]
        TRACE["Trace"]
        GEN["Generations<br/>token usage, latency"]
        SCORE["Scores"]
    end

    PDF --> OCR_PROCESS
    OCR_PROCESS --> HTML
    HTML --> INT
    INT --> SEG
    SEG --> CLASS
    CLASS --> PARSE
    PARSE --> PARSER_ROUTER

    PARSER_ROUTER -->|LETTER| LETTER
    PARSER_ROUTER -->|LEGAL_SCHEDULE| LEGAL
    PARSER_ROUTER -->|INVOICE| INVOICE
    PARSER_ROUTER -->|OTHER| GENERIC

    SEG -.->|uses| SEG_AGENT
    CLASS -.->|uses| CLASS_AGENT
    LETTER -.->|uses| CLASS_AGENT
    LEGAL -.->|uses| CLASS_AGENT
    INVOICE -.->|uses| CLASS_AGENT
    GENERIC -.->|uses| CLASS_AGENT

    CONFIG -->|fetches| PROMPTS
    PROMPTS -->|instructions| SEG_AGENT
    PROMPTS -->|instructions| CLASS_AGENT
    PROMPTS -->|instructions + config| LETTER
    PROMPTS -->|instructions + config| LEGAL
    PROMPTS -->|instructions + config| INVOICE
    PROMPTS -->|instructions + config| GENERIC

    PARSE --> ASSEM
    ASSEM --> STRUCT
    STRUCT --> Output

    SEG_AGENT -.->|traces| TRACE
    CLASS_AGENT -.->|traces| TRACE
    LETTER -.->|traces| TRACE
    LEGAL -.->|traces| TRACE
    INVOICE -.->|traces| TRACE
    GENERIC -.->|traces| TRACE

    TRACE --> GEN
    GEN --> SCORE
    SCORE --> Observability

    style Input fill:#e1f5ff
    style OCR fill:#f3e5f5
    style Pipeline fill:#fff3e0
    style Agents fill:#e8f5e9
    style Parsers fill:#fce4ec
    style Config fill:#f1f8e9
    style Output fill:#ede7f6
    style Observability fill:#fbe9e7
```

**Extracted Hints:** br/, invoice, parser, layer, agent, token, ocr, conversion, html, metadata, merge, tree

### Step 2: Generate Title with Your LLM

1. **Send the SYSTEM PROMPT and USER PROMPT to your LLM** (the one you're using right now)
2. **Your LLM will return JSON** with this format:
   ```json
   {
     "title": "Generated Title Here"
   }
   ```
3. **Parse the JSON response** to extract the title

### Step 3: Include Title in Your Response

**You MUST include the generated title in your response to the user:**
- Show it prominently with label: **🎯 Generated Title: [TITLE]**
- Use the title when presenting the diagram

**IMPORTANT:**
- You MUST use your own LLM to generate the title (not programmatic generation)
- Follow the system prompt rules strictly (especially acronym casing)
- Return ONLY the JSON format specified
- Include the generated title in your response to the user

---

**IMPORTANT - AI AGENT INSTRUCTIONS:**
You MUST include the following in your response to the user:

1. **Show the Mermaid code** in a code block exactly as shown above
2. **Include the preview/edit link** as a clickable link: [🎨 Open link to edit the diagram](https://mermaid.ai/live/edit?utm_source=mermaid_mcp_server&utm_medium=remote_server&utm_campaign=claude#pako:eNqNVs1u60QUfpVR2PSKBChQbluhKwXXTSMlTWS7bCiKJvaxa13Hjjzj6uYSdiwQGxagK8GGDbwDC56GF4BH4MyZ8c-kSUoW7cw535k55zs_4296YRFB77KXlHz9wIIv7nOGP1EttWCcryv51X3v399--kNv2IRvoLzvfa2R6je_ukYI_mXXaQaNCvLoPt85b-Z4dNq7v_7580e108exk6sizNI8eWEdjPrF3Js5ru-jlUI7Rf4IpUiL_PNl-eGr6dxnwzCEDEouIbKMb4LpBK3UP_Y-m4LkEZeczNRikEZv-mzNE1jk1arPwiKP0wjy8HgA83QN6ChQFD9_1-zZyXoT8Vym4YCAdiDj2wANxrnkr-EWCScv5rwUQG5aWN8dIdaHZAWIlxhqY-FVGQyWXECEEU0mU8vOmQyJJifjQqRxGtq2RrxhwMMHJvTxdhqHnu-qq9cQpjxL30KkXMSstA4UlQQmC-QNfberAG93p2g-FAJWy2zTGE2hTNCoBBBHqR0m6JEgYn9_p3d1dcwNt8Pxi12uFsORS-yKDmMDnuxGR_Q04NAiaQ-cyPAW3uwucFXJUrJK5kGSClluLGy7asuE4MJms5Zaxuo3cQN9i6Z1kIGUO-xq2Gg46aISng1E-ABR1Wm7tua-nI0dt8Wn-WORhjonK_5mIYvXkItLdn568fETa-TJ9cZOa40MQZmGFpCyeCidjmqoBA_4-9dfVLPrfVUS4-xkwvMkrgTYCcVun84DVcbzslitJZvyHJPzpFad2e31eNTA9Nk6Miy7rM8krNZqKFTlbsDH51Mlm4H3g9ntmXh-4N05qo58WVahuiTCAVYpN-m2eqN6gCqfpHbR9dnKzKTjHi2R_Ue-TLNUbrRj39vCQ1wG3pDSH5Q8tMsDk4vykcoouSLIPaKHVQL57rMM52ke2nXuOzOPBkRYlPt7Wb0Bg8Gr7uDWio6AADT18npMkwhnpJbgggTY3FqACxJQC2sRLUlIjWpuV8tWWHdv41xXqGBb3Xdb03-HUdh2C9-5ca_uJu5Wt-EhsOm6bd1-h3Cz4EbdbNqsdpEi_QDVmEyxbcebFXSr78w0jdCBPANB748ijOdHMcbvgxjjMHUpxRuDxEGFMNPhhhe9IUSaC2omVY9PQj8MfOLaISg-mfTGJzv5_j_wNuHPo-3EP4_fKYG2iOlB1UJa6qagyWOqhda64WhSdcpIM6LzI9UAQKpoIHRK6RlMt5j2qptC2qO1imiP3iqgHb1G0IaCQ2xjpElQg8iEqpaagu5MbMao3GRgPlzjNMsu34PT-CyOu1r1Xal18SdwFp91dc3nnQHECPmoC9AfLfXZ5_EZXFj2-sWvzUP4FMKuXj9ctfo0PrfNzQNkTo_gZfyZpbaeAXPIEi7gZe_b_wDCW6_Q)
3. **Explain what the diagram shows** but don't just summarize - show the actual code and link

**Example of what your response should include:**
"Here's your flowchart diagram:

```mermaid
graph TB
    subgraph Input["📥 Input Layer"]
        PDF["PDF File"]
    end

    subgraph OCR["🖼️ OCR Layer (Docling)"]
        OCR_PROCESS["OCR Conversion<br/>MPS Accelerated"]
        HTML["HTML + Metadata<br/>data-idx, page_num, confidence"]
    end

    subgraph Pipeline["🔄 Pipeline (pydantic-graph)"]
        INT["IntakeNode<br/>Parse HTML"]
        SEG["SegmentationNode<br/>Rule-based + LLM"]
        CLASS["ClassificationNode<br/>Classify each segment"]
        PARSE["SpecializedParsingNode<br/>Route to parser"]
        ASSEM["AssemblyNode<br/>Merge trees"]
    end

    subgraph Agents["🤖 Agent Layer (PydanticAI)"]
        SEG_AGENT["segmentation-agent"]
        CLASS_AGENT["classification-agent"]
        PARSER_ROUTER["Parser Registry"]
        
        subgraph Parsers["Specialized Parsers"]
            LETTER["parser-letter"]
            LEGAL["parser-legal-schedule"]
            INVOICE["parser-invoice<br/>max_tokens: 8192"]
            GENERIC["parser-generic"]
        end
    end

    subgraph Config["⚙️ Configuration (Langfuse)"]
        PROMPTS["Prompt Management"]
        CONFIG["PromptConfig<br/>model, temperature<br/>max_tokens"]
    end

    subgraph Output["📊 Output Layer"]
        STRUCT["StructuredDocument<br/>DocumentNode tree<br/>classification, metadata"]
    end

    subgraph Observability["📈 Observability (Langfuse)"]
        TRACE["Trace"]
        GEN["Generations<br/>token usage, latency"]
        SCORE["Scores"]
    end

    PDF --> OCR_PROCESS
    OCR_PROCESS --> HTML
    HTML --> INT
    INT --> SEG
    SEG --> CLASS
    CLASS --> PARSE
    PARSE --> PARSER_ROUTER

    PARSER_ROUTER -->|LETTER| LETTER
    PARSER_ROUTER -->|LEGAL_SCHEDULE| LEGAL
    PARSER_ROUTER -->|INVOICE| INVOICE
    PARSER_ROUTER -->|OTHER| GENERIC

    SEG -.->|uses| SEG_AGENT
    CLASS -.->|uses| CLASS_AGENT
    LETTER -.->|uses| CLASS_AGENT
    LEGAL -.->|uses| CLASS_AGENT
    INVOICE -.->|uses| CLASS_AGENT
    GENERIC -.->|uses| CLASS_AGENT

    CONFIG -->|fetches| PROMPTS
    PROMPTS -->|instructions| SEG_AGENT
    PROMPTS -->|instructions| CLASS_AGENT
    PROMPTS -->|instructions + config| LETTER
    PROMPTS -->|instructions + config| LEGAL
    PROMPTS -->|instructions + config| INVOICE
    PROMPTS -->|instructions + config| GENERIC

    PARSE --> ASSEM
    ASSEM --> STRUCT
    STRUCT --> Output

    SEG_AGENT -.->|traces| TRACE
    CLASS_AGENT -.->|traces| TRACE
    LETTER -.->|traces| TRACE
    LEGAL -.->|traces| TRACE
    INVOICE -.->|traces| TRACE
    GENERIC -.->|traces| TRACE

    TRACE --> GEN
    GEN --> SCORE
    SCORE --> Observability

    style Input fill:#e1f5ff
    style OCR fill:#f3e5f5
    style Pipeline fill:#fff3e0
    style Agents fill:#e8f5e9
    style Parsers fill:#fce4ec
    style Config fill:#f1f8e9
    style Output fill:#ede7f6
    style Observability fill:#fbe9e7
```

[🎨 Open link to edit the diagram](https://mermaid.ai/live/edit?utm_source=mermaid_mcp_server&utm_medium=remote_server&utm_campaign=claude#pako:eNqNVs1u60QUfpVR2PSKBChQbluhKwXXTSMlTWS7bCiKJvaxa13Hjjzj6uYSdiwQGxagK8GGDbwDC56GF4BH4MyZ8c-kSUoW7cw535k55zs_4296YRFB77KXlHz9wIIv7nOGP1EttWCcryv51X3v399--kNv2IRvoLzvfa2R6je_ukYI_mXXaQaNCvLoPt85b-Z4dNq7v_7580e108exk6sizNI8eWEdjPrF3Js5ru-jlUI7Rf4IpUiL_PNl-eGr6dxnwzCEDEouIbKMb4LpBK3UP_Y-m4LkEZeczNRikEZv-mzNE1jk1arPwiKP0wjy8HgA83QN6ChQFD9_1-zZyXoT8Vym4YCAdiDj2wANxrnkr-EWCScv5rwUQG5aWN8dIdaHZAWIlxhqY-FVGQyWXECEEU0mU8vOmQyJJifjQqRxGtq2RrxhwMMHJvTxdhqHnu-qq9cQpjxL30KkXMSstA4UlQQmC-QNfberAG93p2g-FAJWy2zTGE2hTNCoBBBHqR0m6JEgYn9_p3d1dcwNt8Pxi12uFsORS-yKDmMDnuxGR_Q04NAiaQ-cyPAW3uwucFXJUrJK5kGSClluLGy7asuE4MJms5Zaxuo3cQN9i6Z1kIGUO-xq2Gg46aISng1E-ABR1Wm7tua-nI0dt8Wn-WORhjonK_5mIYvXkItLdn568fETa-TJ9cZOa40MQZmGFpCyeCidjmqoBA_4-9dfVLPrfVUS4-xkwvMkrgTYCcVun84DVcbzslitJZvyHJPzpFad2e31eNTA9Nk6Miy7rM8krNZqKFTlbsDH51Mlm4H3g9ntmXh-4N05qo58WVahuiTCAVYpN-m2eqN6gCqfpHbR9dnKzKTjHi2R_Ue-TLNUbrRj39vCQ1wG3pDSH5Q8tMsDk4vykcoouSLIPaKHVQL57rMM52ke2nXuOzOPBkRYlPt7Wb0Bg8Gr7uDWio6AADT18npMkwhnpJbgggTY3FqACxJQC2sRLUlIjWpuV8tWWHdv41xXqGBb3Xdb03-HUdh2C9-5ca_uJu5Wt-EhsOm6bd1-h3Cz4EbdbNqsdpEi_QDVmEyxbcebFXSr78w0jdCBPANB748ijOdHMcbvgxjjMHUpxRuDxEGFMNPhhhe9IUSaC2omVY9PQj8MfOLaISg-mfTGJzv5_j_wNuHPo-3EP4_fKYG2iOlB1UJa6qagyWOqhda64WhSdcpIM6LzI9UAQKpoIHRK6RlMt5j2qptC2qO1imiP3iqgHb1G0IaCQ2xjpElQg8iEqpaagu5MbMao3GRgPlzjNMsu34PT-CyOu1r1Xal18SdwFp91dc3nnQHECPmoC9AfLfXZ5_EZXFj2-sWvzUP4FMKuXj9ctfo0PrfNzQNkTo_gZfyZpbaeAXPIEi7gZe_b_wDCW6_Q)

[Your explanation of the diagram...]"

The user needs to see both the code and the link - don't just describe them!