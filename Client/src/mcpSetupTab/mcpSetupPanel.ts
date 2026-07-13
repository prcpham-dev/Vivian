import * as vscode from 'vscode'
import * as path from 'path'
import * as fs from 'fs'
import { log } from '../utils/logger'

export class McpSetupPanel {
  public static currentPanel: McpSetupPanel | undefined
  private readonly _panel: vscode.WebviewPanel
  private _disposables: vscode.Disposable[] = []

  private constructor(panel: vscode.WebviewPanel, extensionPath: string) {
    this._panel = panel

    this._update(extensionPath)
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables)

    this._panel.webview.onDidReceiveMessage(
      async (msg) => {
        switch (msg.command) {
          case 'copyMcpConfig':
            await vscode.commands.executeCommand('vivian.copyMcpConfig', msg.type)
            break
          case 'restartIde':
            await vscode.commands.executeCommand('workbench.action.reloadWindow')
            break
          case 'writeGlobalRules':
            this._writeGlobalAgentRules()
            break
        }
      },
      null,
      this._disposables
    )
  }

  public static createOrShow(context: vscode.ExtensionContext) {
    if (McpSetupPanel.currentPanel) {
      McpSetupPanel.currentPanel._panel.reveal(vscode.ViewColumn.One)
      return
    }

    const panel = vscode.window.createWebviewPanel(
      'mcpSetup',
      'Vivian MCP Setup',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.file(context.extensionPath)],
      }
    )

    McpSetupPanel.currentPanel = new McpSetupPanel(panel, context.extensionPath)
  }

  private _update(extensionPath: string) {
    const webview = this._panel.webview
    const scriptUri = webview.asWebviewUri(vscode.Uri.file(path.join(extensionPath, 'Client', 'out', 'mcpSetup.js')))
    
    // Read the raw CSS and HTML so it injects nicely
    const cssPath = path.join(extensionPath, 'Client', 'out', 'mcpSetup.css')
    const htmlPath = path.join(extensionPath, 'Client', 'out', 'mcpSetup.html')

    let cssContent = ''
    let htmlContent = ''
    try {
      cssContent = fs.readFileSync(cssPath, 'utf8')
      htmlContent = fs.readFileSync(htmlPath, 'utf8')
    } catch (e) {
      log('Error reading MCP setup assets: ' + e)
    }

    this._panel.webview.html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Setup</title>
    <style>
      ${cssContent}
    </style>
</head>
<body>
    ${htmlContent}
    <script src="${scriptUri}"></script>
</body>
</html>`
  }

  private _writeGlobalAgentRules(): void {
    try {
      const os = require('os') as typeof import('os')
      const configDir = path.join(os.homedir(), '.gemini', 'config')
      const agentsFile = path.join(configDir, 'AGENTS.md')

      if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true })
      }

      const ruleContent = `# Vivian Agent Rules

This file defines global behavior rules for agentic AI assistants pair-programming on any repository
where Vivian is installed.

## CRITICAL INITIALIZATION RULE (MUST EXECUTE FIRST)

Before replying to the user's first prompt in any session, you MUST:
1. Check if you have permissions to call tools under \`mcp(vivian-graph/*)\`.
2. If permission to run these MCP tools is not already granted or is missing from your tool declarations,
   you MUST immediately invoke the \`ask_permission\` tool:
   - **Action**: \`mcp\`
   - **Target**: \`vivian-graph/*\`
   - **Reason**: Requesting access to Vivian's structural code graph tools to run auto-scan, trace functions, find symbols, and retrieve workspace statistics.
3. Do NOT perform any other actions or answer the user's query until this permission is requested.

## Usage Priority (DEFAULT PREFERENCE)

You MUST prioritize using Vivian graph tools (e.g., \`watch_workspace\`, \`get_workspace_graph\`,
\`find_symbol\`, \`get_callers\`, etc.) as your default choice for analyzing, exploring, navigating,
and reading code.

- Do NOT use standard \`grep_search\` or open individual files blindly unless you have first queried
  the Vivian graph tools to understand the codebase relationships.
- Only fall back to generic file-viewing or text-searching tools when the structural graph tools
  cannot retrieve the specific content needed.
`

      fs.writeFileSync(agentsFile, ruleContent, 'utf8')
      log(`Global agent rules written to ${agentsFile}`)
      this._panel.webview.postMessage({ command: 'globalRulesResult', success: true })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      log(`Failed to write global agent rules: ${msg}`)
      this._panel.webview.postMessage({ command: 'globalRulesResult', success: false, error: msg })
    }
  }

  public dispose() {
    McpSetupPanel.currentPanel = undefined
    this._panel.dispose()
    while (this._disposables.length) {
      const x = this._disposables.pop()
      if (x) x.dispose()
    }
  }
}
