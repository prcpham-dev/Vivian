# Vivian

Vivian is an intelligent code analysis and vulnerability management tool. It consists of a VS Code extension (Client) and a Python backend service (Server).

## Project Structure

```text
Vivian/
├── Client/                 # VS Code Extension (TypeScript)
│   ├── src/                # Extension source code
│   │   ├── services/       # Sidecar and external service communication (sidecarClient.ts, sidecarManager.ts)
│   │   ├── utils/          # Constants and logging utilities
│   │   ├── vulnManager/    # React Webview for the Vulnerability Manager UI (App.tsx, index.tsx, style.css)
│   │   ├── cacheManager.ts # Caching logic
│   │   ├── extension.ts    # VS Code extension entry point
│   │   ├── graphGenerator.ts
│   │   ├── graphPanel.ts   # Webview panel for the code graph
│   │   ├── vulnManagerPanel.ts # Webview panel for vulnerability management
│   │   └── types.ts        # TypeScript definitions
│   ├── package.json        # Extension manifest and dependencies
│   ├── tsconfig.json       # TypeScript configuration
│   └── esbuild.js          # Build script
│
├── Server/                 # Python Backend (FastAPI / WebSockets)
│   ├── core/               # Core business logic
│   │   ├── agents/         # LLM agents for code analysis, git interaction, and chat
│   │   │   ├── chat_history.py
│   │   │   ├── context_loader.py
│   │   │   ├── git_agent.py
│   │   │   ├── graph_chat.py
│   │   │   ├── prompts.py
│   │   │   ├── state.py
│   │   │   ├── tools.py
│   │   │   └── vuln_agent.py
│   │   ├── scanner/        # Code scanning and parsing logic
│   │   │   ├── constants.py
│   │   │   ├── discovery.py
│   │   │   ├── file_parser.py
│   │   │   ├── graph_builder.py
│   │   │   └── types.py
│   │   └── settings_manager.py
│   ├── handlers/           # Request/WebSocket handlers
│   │   ├── chat.py
│   │   ├── git.py
│   │   ├── graph.py
│   │   ├── scan.py
│   │   ├── settings.py
│   │   └── ws.py           # WebSocket connection handling
│   ├── main.py             # Server entry point
│   ├── requirements.txt    # Python dependencies
│   └── settings.json       # Backend configuration
│
├── Demo.mp4                # Demonstration video
└── PLAN.md                 # Project planning document
```

## Getting Started

### Client
1. Navigate to the `Client` directory.
2. Run `npm install` to install dependencies.
3. Build the extension or run it in debug mode from VS Code.

### Server
1. Navigate to the `Server` directory.
2. Create a virtual environment and install dependencies from `requirements.txt`.
3. Set up the `.env` file with required API keys.
4. Run `python main.py` to start the backend service.
