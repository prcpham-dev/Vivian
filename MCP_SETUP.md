# Vivian MCP Server Integration

Vivian includes a built-in **MCP (Model Context Protocol) Server**, allowing AI agents like **Antigravity** and **Cline** to directly leverage Vivian's graph-aware capabilities to analyze, search, and read your codebase.


## 🔌 Connecting to Your AI Agent (Antigravity/Cline)
Because AI agents run independently of the VS Code extension, you must manually add the Vivian server to your agent's MCP configuration settings. 

You need to provide the absolute paths to two things that Vivian automatically created for you:
1. The **Python Executable** inside the extension's virtual environment.
2. The **`mcp_server.py`** script.

### Where do I paste this?

*   **For Cline:** Click the small **MCP (plug) icon** in the top right of the Cline sidebar in VS Code. This will automatically open a file called `cline_mcp_settings.json`. Paste the snippet directly in there.
*   **For Antigravity:** Open the file located at `~/.gemini/antigravity-ide/mcp.json` (Mac/Linux) or `%USERPROFILE%\.gemini\antigravity-ide\mcp.json` (Windows) and paste the snippet in.

### Configuration Snippets

**For macOS / Linux:**
```json
{
  "mcpServers": {
    "vivian-graph": {
      "command": "/Users/YOUR_USERNAME/.vscode/extensions/prcpham.vivian-vision-VERSION/Server/venv/bin/python",
      "args": ["/Users/YOUR_USERNAME/.vscode/extensions/prcpham.vivian-vision-VERSION/Server/mcp_server.py"],
      "env": {}
    }
  }
}
```

**For Windows:**
```json
{
  "mcpServers": {
    "vivian-graph": {
      "command": "C:\\Users\\YOUR_USERNAME\\.vscode\\extensions\\prcpham.vivian-vision-VERSION\\Server\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\YOUR_USERNAME\\.vscode\\extensions\\prcpham.vivian-vision-VERSION\\Server\\mcp_server.py"],
      "env": {}
    }
  }
}
```

*Note: Replace `YOUR_USERNAME` with your actual system username, and `VERSION` with the currently installed version of Vivian.*

---

## ⚠️ Important Caveat: Extension Updates
VS Code installs extensions into directories that include their version number (e.g., `prcpham.vivian-vision-1.0.4`). 

When Vivian receives an update on the Marketplace (e.g., updating to `1.0.5`), **the directory name will change.** 

This means your AI agent's MCP configuration path will break because it points to the old version folder. **You will need to manually update your MCP settings file with the new version number after every Vivian update.**

## 🏢 Handling Legacy & Enterprise Codebases
When dealing with massive, older monolithic codebases, Vivian's graph architecture truly shines, but it requires a slightly different approach:

*   **Average Size of a Legacy Project:** A typical legacy or enterprise project can range anywhere from **500,000 to over 5,000,000 lines of code**, spanning thousands of tightly-coupled files.
*   **Translating Time to Graph:** For a project of this scale, the initial scan and graph generation might take **a few minutes** to complete. However, Vivian automatically caches the parsed structure, meaning all subsequent opens will load the graph almost instantly!
*   **How to Travel Quickly:** When a graph contains thousands of nodes, manually dragging and zooming the UI is inefficient. Instead, use the integrated **Graph Search** feature to instantly teleport to specific classes/functions, and click on node edges (connections) to traverse directly to dependencies rather than searching for them visually.

## 🛠 Available MCP Tools
Once connected, your AI agent will have access to the following tools:
*   **`get_workspace_graph`**: Retrieves the full Vivian structural knowledge graph for the workspace.
*   **`search_graph_nodes`**: Searches Vivian's parsed graph nodes (functions, classes, interfaces) for specific names or text.
*   **`read_workspace_file`**: Reads the literal text of a file utilizing Vivian's existing robust file-reading utilities.

## 🚀 Future Roadmap & Capabilities

The following features are planned for future updates to enhance the MCP integration:

1. **Automated "Copy MCP Config" Command**
   * *The Versioning Fix:* Since extension updates break the absolute path to the Python executable and server script, we will introduce a `Vivian: Copy MCP Config` command to the VS Code Command Palette. This command will dynamically grab your correct `context.extensionPath`, generate the JSON configuration block, and copy it straight to your clipboard.

2. **Graph-Powered AI Chat Integration**
   * Allow AI agents like Antigravity to fully ingest, query, and navigate the interactive Vivian knowledge graph in order to provide much deeper contextual answers and architecture analysis.

3. **LLM Offloading (API Key Sharing via MCP)**
   * Currently, Vivian's internal tools (like the LangGraph agents and VulnManager) require you to input a dedicated API key within the Vivian settings. 
   * *The Goal:* Utilize MCP's **"Sampling"** capabilities to allow Vivian's internal backend to request LLM responses *directly* from the connected client (Antigravity, Cline, etc.). This means Vivian will securely "hitch a ride" on the client's existing API setup, meaning you won't need to manually configure API keys directly inside Vivian!
