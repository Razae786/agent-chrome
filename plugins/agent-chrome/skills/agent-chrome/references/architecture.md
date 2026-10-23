# Agent Chrome — Technical Architecture

```mermaid
flowchart TD
    USER["User (Eyes on Screen)"]
    AGENT["AI Coding Agent (Claude Code / Antigravity / Cursor)"]

    subgraph BROWSER ["Agent Chrome (:9222 CDP)"]
        TABS["Live Web Sessions<br/>ChatGPT • Claude • DeepSeek • Gemini • Z.ai"]
    end

    subgraph ENGINE ["Local Runtime"]
        BRIDGE["bridge_server.py (:8000)<br/>OpenAI-compatible REST API"]
        COUNCIL["council.py<br/>Consensus & Discrepancy Engine"]
    end

    USER <-->|"Visual Feedback & Interaction"| TABS
    AGENT -->|"POST /v1/chat/completions"| BRIDGE
    AGENT -->|"CLI Consensus Query"| COUNCIL
    COUNCIL --> BRIDGE
    BRIDGE -->|"Chrome DevTools Protocol (CDP)"| TABS
```

### Key Components

1. **Dedicated User Data Dir (`~/.agent-chrome-profile`)**:
   - Completely isolated from your primary personal Chrome browsing data.
   - Preserves active logins so you never need to authenticate more than once.
   - Clean lock hygiene: never locks when closed cleanly.

2. **Chrome DevTools Protocol (CDP)**:
   - Port 9222 allows bi-directional WebSocket and HTTP control.
   - Native DOM observation without injecting heavy browser extensions.

3. **Singleton Bridge Server**:
   - Manages tab concurrency through `asyncio.Lock` per provider.
   - Prevents keystroke collisions when multiple agents or subagents query concurrently.
   - Automatic new turn detection: compares message node count and polls for settled text before returning.
