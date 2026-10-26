---
name: agent-chrome
description: Query your live, visible desktop Chrome browser sessions as a zero-cost Multi-LLM consensus council (Claude Sonnet, DeepSeek R1, ChatGPT, Gemini, Z.ai). No API keys, no GPU VRAM. Trigger via /agent-chrome or /miltillm.
---

# Agent Chrome Skill

Activate this skill when you want to cross-reference multiple state-of-the-art LLMs, verify complex architectural decisions, break out of a single model's blind spots, or avoid burning expensive API tokens.

> [!IMPORTANT]
> **Consensus & Verification Rules**:
> 1. Always wait for all active models to respond before finalizing architectural decisions.
> 2. Read each model's full response — models frequently make distinct false assumptions.
> 3. If models disagree or conflict with project constraints, re-query or probe the divergence until ground truth is confirmed.
> 4. Agent Chrome runs in a **visible desktop window** — the user can watch prompts stream into tabs in real time. Never run headless or lock the profile.

---

## 1. Quick Start

### Step 1: Check System Health
Run the doctor script:
```bash
python scripts/doctor.py
```

### Step 2: Ensure Agent Chrome Is Open
Agent Chrome runs on port `9222`. Launch it from your desktop shortcut or via script:
- **Windows**: `scripts/launch_agent_chrome.bat`
- **macOS / Linux**: `bash scripts/launch_agent_chrome.sh`

### Step 3: Ensure Bridge Server Is Running
The bridge runs on port `8000` exposing standard `/v1/chat/completions`:
```bash
python engine/bridge_server.py
```

---

## 2. Using the Council in Coding Workflows

### Option A: Query the CLI
```bash
# Query all 6 models simultaneously
python engine/council.py -q "What are the edge cases of using an SQLite WAL mode under concurrent multiprocessing?"

# Run Hostile Technical Audit (strips politeness, hunts fatal flaws)
python engine/council.py -q "Audit our memory cascade architecture" --audit

# Audit + Automated 3-Part Consensus Synthesis
python engine/council.py -q "Review this database migration strategy" --audit --synthesize

# Query with deliverable attachments (images, PPTX, PDFs, documents, code)
python engine/council.py -q "Cross-examine this architecture diagram and slide deck" -f arch.png slides.pptx --audit
```

### Option B: Query via OpenAI Client / HTTP
Any OpenAI-compatible SDK can connect directly to `http://127.0.0.1:8000/v1`:

```python
import openai

client = openai.OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="web-claude-sonnet", # or web-deepseek-r1, web-chatgpt, web-gemini, web-zai
    messages=[{"role": "user", "content": "Explain vector search index compaction."}]
)
print(response.choices[0].message.content)
```

---

## 3. Supported Model Identifiers

| Model ID | Provider | Tab Match URL |
|---|---|---|
| `web-claude-sonnet` | Anthropic Claude | `claude.ai` |
| `web-deepseek-r1` | DeepSeek R1 Reasoning | `chat.deepseek.com` |
| `web-chatgpt` | OpenAI ChatGPT | `chatgpt.com` |
| `web-gemini` | Google Gemini | `gemini.google.com` |
| `web-zai` | Z.ai GLM-5.3 | `chat.z.ai` |
| `web-kimi` | Moonshot Kimi K3 | `kimi.ai` |

To add custom providers or change DOM selectors, edit [`engine/selectors.json`](file:///engine/selectors.json).

---

## 4. Hardware & Safety Invariants

- **0 MB GPU VRAM**: Queries execute entirely in Chrome's render processes or remote cloud infrastructure. Your local GPU (e.g. RTX 4050/4090) remains 100% free for local models, IDE, and tasks.
- **Session Privacy**: All cookies and authentication remain isolated in your dedicated profile (`~/.agent-chrome-profile`). Nothing is ever committed or sent to external telemetry.
