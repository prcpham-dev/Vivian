import * as vscode from 'vscode'
import * as fs from 'fs'
import { KnowledgeGraph } from '../types'
import { log } from '../utils/logger'
import { getActivePort } from '../services/sidecarManager'

function getNonce(): string {
  let text = ''
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  for (let i = 0; i < 32; i++) text += chars.charAt(Math.floor(Math.random() * chars.length))
  return text
}

export class GraphPanel {
  static current: GraphPanel | undefined
  private readonly panel: vscode.WebviewPanel
  private disposables: vscode.Disposable[] = []
  private latestGraph: KnowledgeGraph

  static create(context: vscode.ExtensionContext, graph: KnowledgeGraph, workspaceRoot: string): GraphPanel {
    if (GraphPanel.current) {
      GraphPanel.current.panel.reveal(vscode.ViewColumn.One)
      GraphPanel.current.update(graph)
      return GraphPanel.current
    }
    const panel = vscode.window.createWebviewPanel(
      'vivianGraph',
      'Vivian: Code Graph',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'Client', 'out')],
      }
    )
    GraphPanel.current = new GraphPanel(panel, context, graph, workspaceRoot)
    return GraphPanel.current
  }

  private constructor(
    panel: vscode.WebviewPanel,
    private readonly context: vscode.ExtensionContext,
    graph: KnowledgeGraph,
    private readonly workspaceRoot: string
  ) {
    this.panel = panel
    this.latestGraph = graph
    this.panel.webview.html = this.getHtml(getNonce())
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables)
    this.panel.webview.onDidReceiveMessage((msg) => this.onMessage(msg), null, this.disposables)
  }

  update(graph: KnowledgeGraph): void {
    this.latestGraph = graph
    this.panel.webview.postMessage({ command: 'loadGraph', graph })
  }

  private onMessage(msg: { command: string;[key: string]: unknown }): void {
    if (msg.command === 'webviewReady') {
      this.update(this.latestGraph)
    } else if (msg.command === 'saveThemeState') {
      this.context.globalState.update('vivian.themeState', msg.state)
    } else if (msg.command === 'openFile' && typeof msg.filePath === 'string') {
      const folders = vscode.workspace.workspaceFolders
      if (folders?.length) {
        const uri = vscode.Uri.joinPath(folders[0].uri, msg.filePath)
        vscode.window.showTextDocument(uri).then(undefined, () => {
          vscode.window.showTextDocument(vscode.Uri.file(msg.filePath as string))
        })
      }
    } else if (msg.command === 'log') {
      log(`[WebView] ${msg.text}`)
    } else if (msg.command === 'openVulnManager') {
      vscode.commands.executeCommand('vivian.openVulnManager')
    } else if (msg.command === 'openMcpSetup') {
      vscode.commands.executeCommand('vivian.openMcpSetup')
    } else if (msg.command === 'updateSetting' && typeof msg.key === 'string') {
      vscode.workspace.getConfiguration().update(msg.key, msg.value, vscode.ConfigurationTarget.Global).then(() => {
        if (msg.key === 'vivian.aiProvider') {
          this.panel.webview.html = this.getHtml(getNonce())
        }
      })
    } else if (msg.command === 'openProjectsFolder') {
      const os = require('os')
      const p = vscode.Uri.file(os.homedir() + '/.vivian/projects')
      vscode.env.openExternal(p)
    }
  }

  dispose(): void {
    GraphPanel.current = undefined
    this.panel.dispose()
    this.disposables.forEach((d) => d.dispose())
    this.disposables = []
  }

  private getHtml(nonce: string): string {
    const webview = this.panel.webview
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, 'Client', 'out', 'graphApp.js')
    )

    // Inline the CSS so 'unsafe-inline' covers it — avoids CSP issues with <link> in webviews
    let css = ''
    try {
      const cssPath = vscode.Uri.joinPath(this.context.extensionUri, 'Client', 'out', 'graphApp.css').fsPath
      css = fs.readFileSync(cssPath, 'utf8')
    } catch { /* graceful fallback */ }

    const port = getActivePort()
    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}' ${webview.cspSource} https://d3js.org; style-src 'unsafe-inline'; connect-src ws://localhost:${port} http://localhost:${port};">
  <title>Vivian: Code Graph</title>
  <style>${css}</style>
</head>
<body>

<div id="toolbar">
  <div class="search-container">
    <input type="text" id="search" placeholder="Search nodes…" autocomplete="off">
    <button id="clear-search-btn" title="Clear search">Clear</button>
  </div>
  <button id="theme-btn" title="Graph color themes" class="toolbar-btn">Theme</button>
  <button id="switch-to-vuln-btn" title="Switch to Vulnerability Manager" class="toolbar-btn">Vuln Manager</button>
  <div class="filter-group" id="rel-filters">
    <span style="font-size:11px;color:var(--vscode-descriptionForeground,#888)">Relationship:</span>
  </div>
  <div class="filter-group" id="node-filters">
    <span style="font-size:11px;color:var(--vscode-descriptionForeground,#888)">Nodes:</span>
  </div>
  <span id="node-count"></span>
</div>

<div id="main">
  <div id="graph-container">
    <div id="loading">
      <div class="spinner"></div>
      <span>Waiting for graph data…</span>
    </div>
    <svg id="svg"></svg>
    <div id="theme-panel">
      <div id="theme-panel-inner">
        <div id="theme-panel-header">
          <span>Graph Themes</span>
          <button id="close-theme-btn" title="Close">&times;</button>
        </div>
        <div id="theme-tabs">
          <button type="button" id="theme-tab-themes" class="theme-tab active">Themes</button>
          <button type="button" id="theme-tab-custom" class="theme-tab">Custom</button>
        </div>
        <div id="theme-themes-view" class="theme-view">
          <div id="theme-list"></div>
        </div>
        <div id="theme-custom-view" class="theme-view" style="display:none;">
          <div id="theme-custom-colors"></div>
          <div id="theme-save-section">
            <label class="theme-save-label" for="theme-name-input">Theme name</label>
            <input type="text" id="theme-name-input" placeholder="Theme 1" autocomplete="off">
            <button type="button" id="save-theme-btn">Save Theme</button>
            <div id="save-theme-status" class="theme-save-status"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div id="info-panel" style="position:relative;">
    <button id="close-panel-btn" title="Close">×</button>
    <h3 id="info-name"></h3>
    <span id="info-badge" class="badge"></span>
    <div id="info-path" style="font-size:10px;color:var(--vscode-descriptionForeground,#888);word-break:break-all;"></div>
    <button id="open-file-btn" style="display:none;">Open in Editor</button>
    <div id="info-functions"></div>
    <div id="info-imports"></div>
    <div id="info-imported-by"></div>
  </div>
</div>

<div id="tooltip"></div>

<button id="chat-btn" title="Open chat">&#x1F4AC;</button>
<div id="chat-drawer">
  <div id="chat-drawer-header">
    <span>Vivian Chat</span>
    <div style="display:flex;align-items:center;gap:4px;">
      <span style="font-size:11px;color:var(--vscode-descriptionForeground,#888);margin-right:2px;">Built-in AI</span>
      <label class="ai-switch" title="Toggle Internal/External AI">
        <input type="checkbox" id="ai-provider-checkbox">
        <span class="ai-slider"></span>
      </label>
      <button id="chat-settings-btn" title="Settings" style="background:none;border:none;color:var(--vscode-icon-foreground,#c5c5c5);cursor:pointer;font-size:16px;">&#x2699;</button>
      <button id="close-chat-btn" title="Close">&#xD7;</button>
    </div>
  </div>
  <div id="chat-body">
    <div id="api-key-section" style="display:none;">
      <div id="api-key-header">
        <span id="api-key-label">Settings</span>
        <div style="display:flex;gap:8px;">
          <button id="clear-chat-btn" title="Clear chat history" style="background:none;border:1px solid var(--vscode-panel-border,#444);border-radius:3px;color:var(--vscode-foreground,#ccc);cursor:pointer;display:flex;align-items:center;gap:4px;padding:4px 8px;font-size:10px;white-space:nowrap;"><svg style="width:12px;height:12px;" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M6.5 1h3a.5.5 0 0 1 .5.5v1H3v-1a.5.5 0 0 1 .5-.5h3zm-4 2v1h11V3h-11zm1 2v8.5a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5V5h-8zm2 1h1v6h-1V6zm3 0h1v6h-1V6z"/></svg>Clear History</button>
          <button id="open-projects-btn" title="Open Vivian Projects" style="background:none;border:1px solid var(--vscode-panel-border,#444);border-radius:3px;color:var(--vscode-foreground,#ccc);cursor:pointer;display:flex;align-items:center;gap:4px;padding:4px 8px;font-size:10px;white-space:nowrap;"><svg style="width:12px;height:12px;" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.543l-1.6-1.6A1.75 1.75 0 0 0 4.707 1H1.75zM1.5 2.75a.25.25 0 0 1 .25-.25h2.957a.25.25 0 0 1 .177.073l1.6 1.6A.25.25 0 0 0 6.66 4.25H14.25a.25.25 0 0 1 .25.25V5H1.5V2.75zm0 3.75v6.75c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V6.5H1.5z"/></svg>Open Folder</button>
        </div>
      </div>
      <div id="api-key-status"></div>
      <div id="api-key-form-row" style="display:flex;">
        <input type="password" id="api-key-input" placeholder="Paste API key…" autocomplete="off">
        <button id="api-key-save-btn">Save</button>
      </div>
      <div id="model-select-row" style="display:flex;">
        <select id="model-select">
          <option value="gemini-2.5-flash">gemini-2.5-flash</option>
          <option value="gemini-2.5-pro">gemini-2.5-pro</option>
          <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
          <option value="gemini-3.5-flash">gemini-3.5-flash</option>
          <option value="gemini-3.5-pro">gemini-3.5-pro</option>
          <option value="gemini-3.1-pro">gemini-3.1-pro</option>
          <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite</option>
          <option value="gemini-3-pro-deep-think">gemini-3-pro-deep-think</option>
        </select>
        <button id="model-save-btn">Apply</button>
      </div>
    </div>
    <div id="chat-messages"></div>
    <div id="chat-input-area">
      <textarea id="chat-input" placeholder="Ask Vivian…" rows="2"></textarea>
      <button id="chat-send-btn">Send</button>
    </div>
  </div>
</div>

<script nonce="${nonce}" src="https://d3js.org/d3.v7.min.js"></script>
<script nonce="${nonce}">window.WORKSPACE_ROOT = ${JSON.stringify(this.workspaceRoot)};window.SIDECAR_PORT = ${port};window.THEME_STATE = ${JSON.stringify(this.context.globalState.get('vivian.themeState') || null)};window.AI_PROVIDER = ${JSON.stringify(vscode.workspace.getConfiguration('vivian').get('aiProvider') || 'External MCP Client')};</script>
<script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`
  }
}
