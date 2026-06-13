# Vivian — Client (VSCode Extension)

Interactive D3 force-directed code graph rendered inside a VSCode WebView panel.

## Features

- Force-directed graph with nodes for Files, Folders, Classes, Functions, and Interfaces
- Edge types: `IMPORTS`, `CONTAINS`, `CALLS`, `INHERITS`
- Zoom, pan, drag nodes
- Click a node to see its details and connections
- Search bar (Ctrl+F) to highlight nodes by name
- Filter chips to show/hide node types and relationship types
- Open a file node directly in the editor

## Setup

```bash
cd Client
npm install
npm run build
```

Then open the folder in VSCode and press **F5** to launch the Extension Development Host, or install the `.vsix` after packaging.

## Commands

| Command | Description |
|---|---|
| `Vivian: Open Code Graph` | Load `graph.json`, load cache, or build the graph and open the panel |

## Data Format

The graph consumes the `KnowledgeGraph` JSON produced by the Python sidecar (`Server/`). To test the graph without the sidecar, place a `graph.json` file in the workspace root:

```json
{
  "nodes": [
    { "id": "src/app.ts", "label": "File", "properties": { "name": "app.ts", "filePath": "src/app.ts" } }
  ],
  "relationships": [
    { "id": "IMPORTS_src/app.ts->src/types.ts", "type": "IMPORTS", "sourceId": "src/app.ts", "targetId": "src/types.ts", "confidence": 1.0, "reason": "" }
  ],
  "timestamp": 1718000000000
}
```

When `graph.json` is present, the client loads it directly and skips sidecar startup. Otherwise, graph data is cached locally as `.vivian-cache.json` in the workspace root and loaded on subsequent opens without hitting the sidecar.
