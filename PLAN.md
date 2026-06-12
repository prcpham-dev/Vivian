# Vivian — Build Plan

**What:** VSCode extension with a Python AI backend (sidecar).
**Architecture:** Extension (TypeScript) handles the graph UI. Python sidecar (LangGraph + FastAPI) handles all AI — the extension never touches an LLM directly.

---

## Architecture

```
Vivian/
├── Client/                      # VSCode Extension (TypeScript)
│   ├── package.json
│   ├── tsconfig.json
│   ├── esbuild.js
│   ├── .gitignore
│   ├── src/
│   │   ├── extension.ts        # Extension entry point, spawns Python sidecar
│   │   ├── graphGenerator.ts   # Walk, parse, track functions, build graph
│   │   ├── cacheManager.ts     # Save/load graph cache
│   │   ├── graphPanel.ts       # WebView panel, D3 setup, message routing
│   │   ├── types.ts            # Type definitions (FileNode, Edge, FunctionDef)
│   │   ├── services/
│   │   │   ├── sidecarManager.ts  # Spawns & kills FastAPI server
│   │   │   └── sidecarClient.ts   # WebSocket & REST communications
│   │   └── utils/
│   │       ├── constants.ts    # Default extension config, ignores
│   │       └── logger.ts       # Output channel logging
│   └── README.md
├── Server/                      # Sidecar AI Backend (Python + FastAPI)
│   ├── requirements.txt
│   ├── main.py                 # FastAPI Web Server & Websocket setup
│   ├── config.py               # Server configurations
│   ├── agents/                 # LangGraph Agents
│   │   ├── __init__.py
│   │   ├── state.py            # LangGraph shared state schemas
│   │   ├── vuln_agent.py       # Vuln scanners (parallel check)
│   │   ├── refactor_agent.py   # Refactor advice builder
│   │   ├── git_agent.py        # Git assistant diff summarizer
│   │   └── graph_chat.py       # Codebase context-aware chat
│   └── README.md
├── PLAN.md                     # General project plan
└── README.md                   # Repository README
```

---

## Tech Stack

| Part | Tech |
|---|---|
| Extension | TypeScript, VS Code API |
| Graph | D3.js (force simulation, drag, zoom) |
| File parser | TypeScript (regex, no external deps) |
| AI backend | Python, FastAPI, WebSocket |
| Agents | LangGraph |
| LLM | OpenRouter API (called from Python only) |
| Storage | Local JSON files (workspace cache) |

---

## Tasks

### Person 1 — Parser Engine + Smart Graph Filtering

**Goal: own the data layer — make the graph fast, accurate, and noise-free**

- [ ] File discovery — walk a user-selected directory, collect supported files (`.ts .js .py .go .rs .c .cpp`)
- [ ] Import parser — for each file, extract what it imports and what imports it
- [ ] Function parser — for each file, extract function names, params, return type, line number (regex)
- [ ] Cross-file call tracking — which function in file A calls which function in file B
- [ ] Build graph data structure: `{ nodes: FileNode[], links: Edge[], functions: FunctionDef[] }`
- [ ] Cache graph to `.vivian-cache.json` in workspace root
- [ ] **Smart filtering** — strip all nodes whose resolved path is outside the workspace root (kills phantom/library nodes)
- [ ] **Expand ignore patterns** — add `vendor`, `.yarn`, `pnpm-lock`, `generated`, `dist`, `__mocks__`, `.turbo`, `storybook-static` on top of existing list
- [ ] **Filter UI toggle** — expose a setting in the graph panel to show/hide filtered categories (config, docs, build) so devs can focus on source only
- [ ] Spawn Python sidecar process on extension activate, kill on deactivate
- [ ] HTTP + WebSocket client in extension to talk to sidecar (`localhost:PORT`)

**Data types to define:**
```typescript
FileNode { id, label, category, language, functions: FunctionDef[], inDegree, gitScore }
FunctionDef { name, params, returnType, line, calledBy[], calls[] }
Edge { source, target, type }
```

---

### Person 2 — Graph UI + Inline AI Chat Panel

**Goal: build the interactive graph and embed a streaming AI chat directly inside it (same page, no sidebar)**

- [ ] D3 force-directed graph in a VSCode WebView panel
- [ ] Nodes draggable, zoomable, pannable
- [ ] Color by file category (src / test / config / docs) + heatmap modes
- [ ] Click node → info popover shows functions, in-degree, git heat score
- [ ] Click a function → highlight all cross-file edges for that function
- [ ] Vulnerability overlay — nodes glow red/orange/yellow based on severity
- [ ] Search bar — type to find and zoom to a node
- [ ] **Inline AI chat drawer** — floating `💬` button fixed bottom-right; click to slide open a chat panel *inside* the graph WebView (not a separate sidebar)
  - Scrollable message history with streamed token output
  - Text input + Send button
  - Graph context is automatically injected into every message (current selected node, nearby nodes, function list)
  - `{ command: 'chatMessage', text }` → extension → sidecar → stream tokens back via `{ command: 'chatResponse', text, done }`
- [ ] **Impact warning banner** — when a node is selected, show "imported by N files" inline on the graph
- [ ] Function Registry panel — searchable list of all functions across the codebase; click → open file at that line

---

### Person 3 — Python Sidecar (AI Backend + Agents)

**Goal: build the FastAPI + LangGraph backend that does all heavy AI work**

- [ ] FastAPI app with WebSocket endpoint (`/ws`) and REST endpoints
- [ ] WebSocket streaming — push tokens and findings to extension as they are discovered
- [ ] OpenRouter client — make LLM calls, stream tokens back to extension
- [ ] **Graph-context chat endpoint** (`POST /chat`)
  - Receives: user message + compact graph summary JSON + selected node context
  - Graph summary format per file: `{ file, functions[], imports_from[], imported_by[] }`
  - Builds a smart system prompt from the graph, calls LLM, streams response back
  - ~200 tokens per file — full codebase fits in one context window
- [ ] **Vulnerability scan agent** (`POST /scan/directory`)
  - Receives: list of files + their content (from selected directory only)
  - LangGraph agents run in parallel: XSS checker, SQLi checker, Auth checker
  - Each finding streamed immediately via WebSocket
  - Returns: `{ file, line, type, severity, snippet, fix }`
- [ ] **Single file scan** (`POST /scan/file`) — same agents, focused on one file
- [ ] **Diff scan** (`POST /scan/diff`)
  - Receives: `git diff --cached` output
  - Agents scan only the changed lines and return findings
- [ ] **Impact analysis** (`POST /analyze/impact`)
  - Receives: graph JSON + file being edited
  - Returns: list of files that depend on it + risk estimate
- [ ] **Git assistant** (`POST /git/summarize`)
  - Receives: `git diff` + graph JSON
  - Returns: commit message suggestion + change impact summary
- [ ] **Refactor advisor** (`POST /analyze/refactor`) ← new
  - Receives: a node + its full source + its neighbours from the graph
  - Returns: concrete refactoring suggestions (extract function, reduce coupling, rename for clarity)
  - Streamed back to the inline chat panel

---

## Build Order

1. **Person 1** finishes file discovery + graph data structure + filtering first — everyone depends on clean graph data
2. **Person 3** sets up FastAPI skeleton + WebSocket early so Person 1 can wire the sidecar connection
3. **Person 2** can build the D3 graph and chat drawer using mock data while Persons 1 and 3 finish their pieces
4. Wire chat: Person 2's `chatMessage` → Person 1's WS client → Person 3's `/chat` → stream back to Person 2's drawer
5. Hook up vulnerability overlay (Person 2 UI) to scan results (Person 3 agents) last

---

## Scope Rule

**Directory-scoped always.** User picks a directory at the start. The graph, all scans, and all AI context stay within that directory. Never scan the whole repo by default — controls token cost and keeps results relevant.

Library and vendor files (anything outside the workspace root or matching ignore patterns) are **always excluded** from the graph. No exceptions — this is what keeps the graph readable.

Diff scan is the one exception — it reads `git diff --cached` which is already scoped to what the user staged.
