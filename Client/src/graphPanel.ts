import * as vscode from 'vscode'
import { KnowledgeGraph } from './types'
import { log } from './utils/logger'

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
        localResourceRoots: [],
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
    this.panel.webview.html = this.getHtml(getNonce(), this.workspaceRoot)
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables)
    this.panel.webview.onDidReceiveMessage((msg) => this.onMessage(msg), null, this.disposables)
    // Brief delay to let the webview JS initialize before sending data
    setTimeout(() => this.update(graph), 300)
  }

  update(graph: KnowledgeGraph): void {
    this.panel.webview.postMessage({ command: 'loadGraph', graph })
  }

  private onMessage(msg: { command: string; [key: string]: unknown }): void {
    if (msg.command === 'openFile' && typeof msg.filePath === 'string') {
      const folders = vscode.workspace.workspaceFolders
      if (folders?.length) {
        const uri = vscode.Uri.joinPath(folders[0].uri, msg.filePath)
        vscode.window.showTextDocument(uri).then(undefined, () => {
          // Try absolute path fallback
          vscode.window.showTextDocument(vscode.Uri.file(msg.filePath as string))
        })
      }
    } else if (msg.command === 'log') {
      log(`[WebView] ${msg.text}`)
    }
  }

  dispose(): void {
    GraphPanel.current = undefined
    this.panel.dispose()
    this.disposables.forEach((d) => d.dispose())
    this.disposables = []
  }

  private getHtml(nonce: string, workspaceRoot: string): string {
    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}' https://d3js.org; style-src 'unsafe-inline'; connect-src ws://localhost:8765 http://localhost:8765;">
<title>Vivian: Code Graph</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--vscode-font-family, 'Segoe UI', sans-serif);
    font-size: 13px;
    background: var(--vscode-editor-background, #1e1e1e);
    color: var(--vscode-editor-foreground, #d4d4d4);
    overflow: hidden;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Toolbar ─────────────────────────────────────────── */
  #toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--vscode-sideBar-background, #252526);
    border-bottom: 1px solid var(--vscode-panel-border, #333);
    flex-shrink: 0;
    flex-wrap: wrap;
  }

  #toolbar input[type="text"] {
    flex: 1;
    min-width: 140px;
    max-width: 260px;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--vscode-input-border, #555);
    background: var(--vscode-input-background, #3c3c3c);
    color: var(--vscode-input-foreground, #d4d4d4);
    font-size: 12px;
    outline: none;
  }

  #toolbar input[type="text"]:focus {
    border-color: var(--vscode-focusBorder, #007acc);
  }

  .filter-group {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 12px;
    cursor: pointer;
    font-size: 11px;
    border: 1px solid transparent;
    user-select: none;
    opacity: 0.6;
    transition: opacity 0.15s, border-color 0.15s;
  }
  .chip.active { opacity: 1; border-color: currentColor; }
  .chip-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

  #node-count {
    margin-left: auto;
    font-size: 11px;
    color: var(--vscode-descriptionForeground, #888);
    white-space: nowrap;
  }

  /* ── Main area ─────────────────────────────────────────── */
  #main {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  #graph-container {
    flex: 1;
    position: relative;
    overflow: hidden;
  }

  svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  /* ── Links ─────────────────────────────────────────── */
  .link {
    stroke-opacity: 0.5;
    stroke-width: 1.2;
    fill: none;
    pointer-events: none;
  }
  .link.IMPORTS  { stroke: #64B5F6; }
  .link.CONTAINS { stroke: #607D8B; stroke-dasharray: 3,3; }
  .link.CALLS    { stroke: #FFD54F; }
  .link.INHERITS { stroke: #CE93D8; stroke-dasharray: 5,2; }
  .link.highlighted { stroke-opacity: 0.9; stroke-width: 2.4; }

  /* ── Nodes ─────────────────────────────────────────── */
  .node circle {
    stroke: rgba(255,255,255,0.15);
    stroke-width: 1;
    cursor: pointer;
    transition: stroke-width 0.1s;
  }
  .node circle:hover { stroke-width: 2.5; stroke: white; }
  .node.selected circle { stroke: white; stroke-width: 2.5; }
  .node.dimmed circle { opacity: 0.15; }
  .node.dimmed text { opacity: 0.15; }

  .node text {
    font-size: 10px;
    fill: var(--vscode-editor-foreground, #d4d4d4);
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
  }
  .node .label-text {
    font-size: 9px;
    dy: 0;
  }

  /* ── Side panel ─────────────────────────────────────────── */
  #info-panel {
    width: 260px;
    min-width: 260px;
    background: var(--vscode-sideBar-background, #252526);
    border-left: 1px solid var(--vscode-panel-border, #333);
    overflow-y: auto;
    padding: 12px;
    display: none;
    flex-direction: column;
    gap: 10px;
  }
  #info-panel.visible { display: flex; }

  #info-panel h3 {
    font-size: 13px;
    font-weight: 600;
    word-break: break-all;
  }
  #info-panel .badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
    margin-bottom: 4px;
  }
  #info-panel .section-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--vscode-descriptionForeground, #888);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }
  #info-panel .func-item {
    padding: 3px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-family: var(--vscode-editor-font-family, monospace);
    cursor: pointer;
    background: var(--vscode-editor-background, #1e1e1e);
    margin-bottom: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  #info-panel .func-item:hover { background: var(--vscode-list-hoverBackground, #2a2d2e); }
  #info-panel .rel-item {
    font-size: 11px;
    padding: 2px 4px;
    margin-bottom: 2px;
    word-break: break-all;
    color: var(--vscode-textLink-foreground, #6daeff);
    cursor: pointer;
  }
  #info-panel .rel-item:hover { text-decoration: underline; }
  #open-file-btn {
    padding: 5px 10px;
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #fff);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
    text-align: center;
  }
  #open-file-btn:hover { background: var(--vscode-button-hoverBackground, #1177bb); }
  #close-panel-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: none;
    border: none;
    color: var(--vscode-icon-foreground, #c5c5c5);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 2px 4px;
  }

  /* ── Tooltip ─────────────────────────────────────────── */
  #tooltip {
    position: fixed;
    pointer-events: none;
    background: var(--vscode-editorHoverWidget-background, #252526);
    border: 1px solid var(--vscode-editorHoverWidget-border, #454545);
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
    max-width: 240px;
    z-index: 1000;
    opacity: 0;
    transition: opacity 0.1s;
  }
  #tooltip.visible { opacity: 1; }

  /* ── Loading ─────────────────────────────────────────── */
  #loading {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    background: var(--vscode-editor-background, #1e1e1e);
    z-index: 10;
  }
  #loading .spinner {
    width: 36px; height: 36px;
    border: 3px solid rgba(255,255,255,0.1);
    border-top-color: var(--vscode-progressBar-background, #0e70c0);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Chat button & drawer ────────────────────────────── */
  #chat-btn {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #fff);
    border: none;
    cursor: pointer;
    font-size: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    z-index: 2000;
    transition: background 0.15s, transform 0.15s;
  }
  #chat-btn:hover { background: var(--vscode-button-hoverBackground, #1177bb); transform: scale(1.08); }

  #chat-drawer {
    position: fixed;
    bottom: 72px;
    right: 20px;
    width: 320px;
    height: 460px;
    background: var(--vscode-sideBar-background, #252526);
    border: 1px solid var(--vscode-panel-border, #444);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    z-index: 1999;
    display: none;
    flex-direction: column;
    overflow: hidden;
  }
  #chat-drawer.open { display: flex; }

  #chat-drawer-header {
    padding: 10px 14px;
    border-bottom: 1px solid var(--vscode-panel-border, #444);
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }
  #close-chat-btn {
    background: none;
    border: none;
    color: var(--vscode-icon-foreground, #c5c5c5);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 2px 4px;
  }

  #chat-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .chat-msg {
    max-width: 88%;
    padding: 7px 10px;
    border-radius: 8px;
    font-size: 12px;
    line-height: 1.5;
    word-break: break-word;
    white-space: pre-wrap;
  }
  .chat-msg.user {
    align-self: flex-end;
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #fff);
    border-bottom-right-radius: 2px;
  }
  .chat-msg.ai {
    align-self: flex-start;
    background: var(--vscode-editor-background, #1e1e1e);
    color: var(--vscode-editor-foreground, #d4d4d4);
    border: 1px solid var(--vscode-panel-border, #444);
    border-bottom-left-radius: 2px;
  }
  .chat-msg.ai.streaming::after {
    content: '\x15ae';
    animation: blink 0.7s step-start infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }

  .chat-status {
    align-self: center;
    font-size: 11px;
    color: var(--vscode-descriptionForeground, #888);
    font-style: italic;
  }

  #chat-input-area {
    display: flex;
    gap: 6px;
    padding: 8px 10px;
    border-top: 1px solid var(--vscode-panel-border, #444);
    align-items: flex-end;
    flex-shrink: 0;
  }
  #chat-input {
    flex: 1;
    resize: none;
    padding: 6px 8px;
    border-radius: 4px;
    border: 1px solid var(--vscode-input-border, #555);
    background: var(--vscode-input-background, #3c3c3c);
    color: var(--vscode-input-foreground, #d4d4d4);
    font-size: 12px;
    font-family: var(--vscode-font-family, 'Segoe UI', sans-serif);
    outline: none;
    line-height: 1.4;
    max-height: 80px;
    overflow-y: auto;
  }
  #chat-input:focus { border-color: var(--vscode-focusBorder, #007acc); }
  #chat-send-btn {
    padding: 6px 12px;
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #fff);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    flex-shrink: 0;
  }
  #chat-send-btn:hover { background: var(--vscode-button-hoverBackground, #1177bb); }
  #chat-send-btn:disabled { opacity: 0.45; cursor: default; }

  /* ── API key section ─────────────────────────────────── */
  #api-key-section {
    border-bottom: 1px solid var(--vscode-panel-border, #444);
    padding: 8px 12px;
    flex-shrink: 0;
  }
  #api-key-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }
  #api-key-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--vscode-descriptionForeground, #888);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  #api-key-toggle-btn {
    background: none;
    border: none;
    color: var(--vscode-icon-foreground, #c5c5c5);
    cursor: pointer;
    font-size: 10px;
    padding: 0 2px;
    line-height: 1;
  }
  #api-key-form-row {
    display: flex;
    gap: 6px;
    align-items: center;
    margin-bottom: 4px;
  }
  #api-key-input {
    flex: 1;
    padding: 5px 8px;
    border-radius: 4px;
    border: 1px solid var(--vscode-input-border, #555);
    background: var(--vscode-input-background, #3c3c3c);
    color: var(--vscode-input-foreground, #d4d4d4);
    font-size: 11px;
    font-family: var(--vscode-font-family, 'Segoe UI', sans-serif);
    outline: none;
  }
  #api-key-input:focus { border-color: var(--vscode-focusBorder, #007acc); }
  #api-key-save-btn {
    padding: 4px 10px;
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #fff);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    flex-shrink: 0;
  }
  #api-key-save-btn:hover { background: var(--vscode-button-hoverBackground, #1177bb); }
  #api-key-save-btn:disabled { opacity: 0.45; cursor: default; }
  #api-key-status {
    font-size: 10px;
    color: var(--vscode-descriptionForeground, #888);
    min-height: 13px;
  }
</style>
</head>
<body>

<div id="toolbar">
  <input type="text" id="search" placeholder="Search nodes…" autocomplete="off">
  <div class="filter-group" id="rel-filters">
    <span style="font-size:11px;color:var(--vscode-descriptionForeground,#888)">Show:</span>
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
    <button id="close-chat-btn" title="Close">&#xD7;</button>
  </div>
  <div id="chat-body">
    <div id="api-key-section">
      <div id="api-key-header">
        <span id="api-key-label">Gemini API Key</span>
        <button id="api-key-toggle-btn" title="Toggle">&#x25BC;</button>
      </div>
      <div id="api-key-form-row">
        <input type="password" id="api-key-input" placeholder="Paste API key&#x2026;" autocomplete="off">
        <button id="api-key-save-btn">Save</button>
      </div>
      <div id="api-key-status"></div>
    </div>
    <div id="chat-messages"></div>
    <div id="chat-input-area">
      <textarea id="chat-input" placeholder="Ask Vivian&#x2026;" rows="2"></textarea>
      <button id="chat-send-btn">Send</button>
    </div>
  </div>
</div>

<script nonce="${nonce}" src="https://d3js.org/d3.v7.min.js"></script>
<script nonce="${nonce}">
(function () {
  'use strict'

  // ── Constants ────────────────────────────────────────
  const NODE_COLORS = {
    File:      '#4FC3F7',
    Folder:    '#78909C',
    Class:     '#FFB74D',
    Function:  '#81C784',
    Interface: '#CE93D8',
    Struct:    '#F48FB1',
    Enum:      '#80CBC4',
    Record:    '#A5D6A7',
  }

  const LINK_COLORS = {
    IMPORTS:  '#64B5F6',
    CONTAINS: '#607D8B',
    CALLS:    '#FFD54F',
    INHERITS: '#CE93D8',
  }

  const NODE_RADII = {
    File:      9,
    Folder:    11,
    Class:     8,
    Function:  6,
    Interface: 7,
    Struct:    7,
    Enum:      6,
    Record:    6,
  }

  // ── State ────────────────────────────────────────────
  let graphData = null
  let activeRelTypes  = new Set(['IMPORTS', 'CALLS', 'INHERITS', 'CONTAINS'])
  let activeNodeTypes = new Set(['File', 'Folder', 'Class', 'Function', 'Interface', 'Struct', 'Enum', 'Record'])
  let selectedNode    = null
  let simulation      = null

  // ── D3 refs ──────────────────────────────────────────
  const svg     = d3.select('#svg')
  const rootG   = svg.append('g')
  const linksG  = rootG.append('g').attr('class', 'links-layer')
  const nodesG  = rootG.append('g').attr('class', 'nodes-layer')
  const arrowG  = svg.append('defs')

  // Arrow marker per relationship type
  Object.entries(LINK_COLORS).forEach(([type, color]) => {
    arrowG.append('marker')
      .attr('id', 'arrow-' + type)
      .attr('viewBox', '0 -4 8 8')
      .attr('refX', 18)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', color)
        .attr('opacity', 0.6)
  })

  // ── Zoom ─────────────────────────────────────────────
  const zoom = d3.zoom()
    .scaleExtent([0.05, 4])
    .on('zoom', (event) => rootG.attr('transform', event.transform))

  svg.call(zoom)
  svg.on('dblclick.zoom', null)
  svg.on('click', (event) => {
    if (event.target === svg.node() || event.target.tagName === 'svg') clearSelection()
  })

  // ── VSCode messaging ─────────────────────────────────
  const vscode = acquireVsCodeApi()

  window.addEventListener('message', (event) => {
    const msg = event.data
    if (msg.command === 'loadGraph') renderGraph(msg.graph)
  })

  // ── Build filter chips ────────────────────────────────
  function buildFilterChips() {
    const relContainer  = document.getElementById('rel-filters')
    const nodeContainer = document.getElementById('node-filters')

    // Clear old chips (keep the label spans)
    ;[...relContainer.querySelectorAll('.chip')].forEach(e => e.remove())
    ;[...nodeContainer.querySelectorAll('.chip')].forEach(e => e.remove())

    // Relationship chips
    const relTypes = [...new Set(graphData.relationships.map(r => r.type))]
    relTypes.forEach(type => {
      const chip = document.createElement('span')
      chip.className = 'chip active'
      chip.style.color = LINK_COLORS[type] || '#aaa'
      chip.innerHTML = \`<span class="chip-dot" style="background:\${LINK_COLORS[type] || '#aaa'}"></span>\${type}\`
      chip.dataset.type = type
      chip.addEventListener('click', () => {
        if (activeRelTypes.has(type)) activeRelTypes.delete(type)
        else activeRelTypes.add(type)
        chip.classList.toggle('active')
        applyFilters()
      })
      relContainer.appendChild(chip)
    })

    // Node type chips
    const nodeTypes = [...new Set(graphData.nodes.map(n => n.label))]
    nodeTypes.forEach(type => {
      const chip = document.createElement('span')
      chip.className = 'chip active'
      chip.style.color = NODE_COLORS[type] || '#aaa'
      chip.innerHTML = \`<span class="chip-dot" style="background:\${NODE_COLORS[type] || '#aaa'}"></span>\${type}\`
      chip.dataset.type = type
      chip.addEventListener('click', () => {
        if (activeNodeTypes.has(type)) activeNodeTypes.delete(type)
        else activeNodeTypes.add(type)
        chip.classList.toggle('active')
        applyFilters()
      })
      nodeContainer.appendChild(chip)
    })
  }

  // ── Main render ───────────────────────────────────────
  function renderGraph(data) {
    graphData = data
    document.getElementById('loading').style.display = 'none'

    buildFilterChips()

    const nodeMap = new Map(data.nodes.map(n => [n.id, n]))
    const validIds = new Set(data.nodes.map(n => n.id))

    // Build D3 node/link arrays
    const nodes = data.nodes.map(n => ({
      id: n.id,
      label: n.label,
      name: n.properties.name,
      filePath: n.properties.filePath,
      functions: n.properties.functions || [],
      classes: n.properties.classes || [],
      interfaces: n.properties.interfaces || [],
      r: NODE_RADII[n.label] || 7,
    }))

    const links = data.relationships
      .filter(r => validIds.has(r.sourceId) && validIds.has(r.targetId))
      .map(r => ({
        source: r.sourceId,
        target: r.targetId,
        type:   r.type,
        id:     r.id,
      }))

    // Destroy old simulation
    if (simulation) simulation.stop()

    const { width, height } = document.getElementById('svg').getBoundingClientRect()
    const cx = width  / 2 || 600
    const cy = height / 2 || 400

    simulation = d3.forceSimulation(nodes)
      .force('link',      d3.forceLink(links).id(d => d.id).distance(d => d.type === 'CONTAINS' ? 60 : 120))
      .force('charge',    d3.forceManyBody().strength(d => d.label === 'File' ? -350 : -150))
      .force('center',    d3.forceCenter(cx, cy))
      .force('collision', d3.forceCollide(d => d.r + 4))
      .force('x',         d3.forceX(cx).strength(0.04))
      .force('y',         d3.forceY(cy).strength(0.04))
      .alphaDecay(0.03)

    // ── Links ────────────────────────────
    const link = linksG.selectAll('.link')
      .data(links, d => d.id)
      .join('line')
        .attr('class', d => 'link ' + d.type)
        .attr('marker-end', d => \`url(#arrow-\${d.type})\`)

    // ── Nodes ────────────────────────────
    const node = nodesG.selectAll('.node')
      .data(nodes, d => d.id)
      .join('g')
        .attr('class', 'node')
        .call(d3.drag()
          .on('start', dragStart)
          .on('drag',  dragged)
          .on('end',   dragEnd))
        .on('click', (event, d) => { event.stopPropagation(); selectNode(d, node, link) })
        .on('mouseover', showTooltip)
        .on('mousemove', moveTooltip)
        .on('mouseout',  hideTooltip)

    node.append('circle').attr('r', d => d.r).attr('fill', d => NODE_COLORS[d.label] || '#aaa')
    node.append('text').attr('dy', d => d.r + 10).attr('class', 'label-text').text(d => truncate(d.name, 18))

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => clamp(d.target, d.type)).attr('y2', d => clampY(d.target, d.type))

      node.attr('transform', d => \`translate(\${d.x},\${d.y})\`)
    })

    document.getElementById('node-count').textContent =
      \`\${nodes.length} nodes · \${links.length} edges\`

    applyFilters()
  }

  // Push links back so they don't overlap the node center
  function clamp(d, type) {
    const r = d.r || 9
    return d.x
  }
  function clampY(d, type) {
    return d.y
  }

  // ── Filters ───────────────────────────────────────────
  function applyFilters() {
    if (!graphData) return
    const searchTerm = document.getElementById('search').value.trim().toLowerCase()
    const visibleNodeIds = new Set(
      graphData.nodes
        .filter(n => activeNodeTypes.has(n.label))
        .map(n => n.id)
    )

    linksG.selectAll('.link').style('display', d =>
      activeRelTypes.has(d.type) &&
      visibleNodeIds.has(typeof d.source === 'object' ? d.source.id : d.source) &&
      visibleNodeIds.has(typeof d.target === 'object' ? d.target.id : d.target)
        ? null
        : 'none'
    )

    nodesG.selectAll('.node').style('display', d =>
      activeNodeTypes.has(d.label) ? null : 'none'
    )

    if (searchTerm) {
      const matched = new Set()
      nodesG.selectAll('.node').each(d => {
        if (d.name.toLowerCase().includes(searchTerm) || d.id.toLowerCase().includes(searchTerm)) {
          matched.add(d.id)
        }
      })

      nodesG.selectAll('.node')
        .classed('dimmed', d => !matched.has(d.id))

      if (matched.size > 0) {
        const first = nodesG.selectAll('.node').filter(d => matched.has(d.id)).datum()
        if (first) panToNode(first)
      }
    } else {
      nodesG.selectAll('.node').classed('dimmed', false)
    }
  }

  // ── Selection ────────────────────────────────────────
  function selectNode(d, nodeSel, linkSel) {
    selectedNode = d
    nodesSel = nodesSel || nodesG.selectAll('.node')
    const linksSel = linksG.selectAll('.link')

    nodesG.selectAll('.node').classed('selected', n => n.id === d.id)

    const connectedIds = new Set([d.id])
    linksSel.each(l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source
      const tid = typeof l.target === 'object' ? l.target.id : l.target
      if (sid === d.id || tid === d.id) {
        connectedIds.add(sid)
        connectedIds.add(tid)
      }
    })

    nodesG.selectAll('.node').classed('dimmed', n => !connectedIds.has(n.id))
    linksSel
      .classed('highlighted', l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return sid === d.id || tid === d.id
      })

    showInfoPanel(d, connectedIds)
  }

  let nodesSel = null

  function clearSelection() {
    selectedNode = null
    nodesG.selectAll('.node').classed('selected', false).classed('dimmed', false)
    linksG.selectAll('.link').classed('highlighted', false)
    document.getElementById('info-panel').classList.remove('visible')
  }

  // ── Info panel ────────────────────────────────────────
  function showInfoPanel(d, connectedIds) {
    const panel = document.getElementById('info-panel')
    panel.classList.add('visible')

    document.getElementById('info-name').textContent = d.name
    const badge = document.getElementById('info-badge')
    badge.textContent = d.label
    badge.style.background = (NODE_COLORS[d.label] || '#888') + '33'
    badge.style.color = NODE_COLORS[d.label] || '#888'

    const pathEl = document.getElementById('info-path')
    pathEl.textContent = d.filePath || d.id

    const openBtn = document.getElementById('open-file-btn')
    openBtn.style.display = (d.label === 'File') ? 'block' : 'none'
    openBtn.onclick = () => vscode.postMessage({ command: 'openFile', filePath: d.filePath || d.id })

    // Functions
    const funcEl = document.getElementById('info-functions')
    if (d.functions && d.functions.length) {
      funcEl.innerHTML = \`<div class="section-title">Functions (\${d.functions.length})</div>\` +
        d.functions.map(f => \`<div class="func-item" title="\${f.name}">\${f.name}\${f.params ? '(' + f.params + ')' : '()'}\${f.returnType ? ': ' + f.returnType : ''}</div>\`).join('')
    } else {
      funcEl.innerHTML = ''
    }

    // Connected nodes
    const importsEl = document.getElementById('info-imports')
    const importedByEl = document.getElementById('info-imported-by')

    if (!graphData) return

    const visibleNodeIds = new Set(
      graphData.nodes
        .filter(n => activeNodeTypes.has(n.label))
        .map(n => n.id)
    )

    const outgoing = graphData.relationships.filter(r => {
      const sid = r.sourceId
      return sid === d.id && activeRelTypes.has(r.type) && visibleNodeIds.has(r.targetId)
    })
    const incoming = graphData.relationships.filter(r => {
      const tid = r.targetId
      return tid === d.id && activeRelTypes.has(r.type) && visibleNodeIds.has(r.sourceId)
    })

    const nodeNameMap = new Map(graphData.nodes.map(n => [n.id, n.properties.name]))

    if (outgoing.length) {
      importsEl.innerHTML = \`<div class="section-title">References (\${outgoing.length})</div>\` +
        outgoing.map(r => \`<div class="rel-item" data-id="\${r.targetId}">\${r.type} → \${nodeNameMap.get(r.targetId) || r.targetId}</div>\`).join('')
    } else {
      importsEl.innerHTML = ''
    }

    if (incoming.length) {
      importedByEl.innerHTML = \`<div class="section-title">Referenced by (\${incoming.length})</div>\` +
        incoming.map(r => \`<div class="rel-item" data-id="\${r.sourceId}">\${r.type} ← \${nodeNameMap.get(r.sourceId) || r.sourceId}</div>\`).join('')
    } else {
      importedByEl.innerHTML = ''
    }

    // Click to pan to related node
    panel.querySelectorAll('.rel-item').forEach(el => {
      el.addEventListener('click', () => {
        const targetId = el.dataset.id
        const targetDatum = nodesG.selectAll('.node').filter(n => n.id === targetId).datum()
        if (targetDatum) panToNode(targetDatum)
      })
    })
  }

  document.getElementById('close-panel-btn').addEventListener('click', clearSelection)

  // ── Pan to node ───────────────────────────────────────
  function panToNode(d) {
    const svgEl = document.getElementById('svg')
    const { width, height } = svgEl.getBoundingClientRect()
    const scale = 1.2
    const tx = width / 2 - scale * d.x
    const ty = height / 2 - scale * d.y
    svg.transition().duration(600)
      .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale))
  }

  // ── Drag ─────────────────────────────────────────────
  function dragStart(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    d.fx = d.x; d.fy = d.y
  }
  function dragged(event, d) {
    d.fx = event.x; d.fy = event.y
  }
  function dragEnd(event, d) {
    if (!event.active) simulation.alphaTarget(0)
    d.fx = null; d.fy = null
  }

  // ── Tooltip ──────────────────────────────────────────
  const tooltip = document.getElementById('tooltip')
  function showTooltip(event, d) {
    const fCount = (d.functions || []).length
    const cCount = (d.classes   || []).length
    tooltip.innerHTML = \`<strong>\${d.name}</strong><br><span style="color:#888">\${d.label}</span>\` +
      (fCount ? \`<br>\${fCount} function\${fCount === 1 ? '' : 's'}\` : '') +
      (cCount ? \`<br>\${cCount} class\${cCount === 1 ? '' : 'es'}\` : '') +
      \`<br><span style="color:#888;font-size:10px">\${d.id}</span>\`
    tooltip.classList.add('visible')
    moveTooltip(event)
  }
  function moveTooltip(event) {
    tooltip.style.left = (event.clientX + 14) + 'px'
    tooltip.style.top  = (event.clientY - 10) + 'px'
  }
  function hideTooltip() {
    tooltip.classList.remove('visible')
  }

  // ── Search ───────────────────────────────────────────
  document.getElementById('search').addEventListener('input', applyFilters)
  document.getElementById('search').addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.target.value = ''; applyFilters() }
  })

  // ── Helpers ──────────────────────────────────────────
  function truncate(str, max) {
    return str && str.length > max ? str.slice(0, max - 1) + '…' : (str || '')
  }

  // ── Keyboard shortcuts ────────────────────────────────
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') clearSelection()
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault()
      document.getElementById('search').focus()
    }
  })

  // ── Chat drawer & WebSocket ───────────────────────────
  const WORKSPACE_ROOT = ${JSON.stringify(workspaceRoot)}
  const WS_URL = 'ws://localhost:8765/ws'

  const chatBtn      = document.getElementById('chat-btn')
  const chatDrawer   = document.getElementById('chat-drawer')
  const closeChatBtn = document.getElementById('close-chat-btn')
  const chatMessages = document.getElementById('chat-messages')
  const chatInput    = document.getElementById('chat-input')
  const chatSendBtn  = document.getElementById('chat-send-btn')

  chatBtn.addEventListener('click', () => chatDrawer.classList.toggle('open'))
  closeChatBtn.addEventListener('click', () => chatDrawer.classList.remove('open'))

  let ws = null
  let wsReady = false
  let currentAiMsg = null

  function appendMsg(role, text) {
    const div = document.createElement('div')
    div.className = 'chat-msg ' + role
    div.textContent = text
    chatMessages.appendChild(div)
    chatMessages.scrollTop = chatMessages.scrollHeight
    return div
  }

  function appendStatus(text) {
    const div = document.createElement('div')
    div.className = 'chat-status'
    div.textContent = text
    chatMessages.appendChild(div)
    chatMessages.scrollTop = chatMessages.scrollHeight
    return div
  }

  function setSendEnabled(enabled) {
    chatSendBtn.disabled = !enabled
    chatInput.disabled = !enabled
  }

  function connectWs() {
    const statusEl = appendStatus('Connecting…')
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      ws.send(JSON.stringify({ event: 'init' }))
    }

    ws.onmessage = (ev) => {
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      if (data.event === 'ready') {
        statusEl.remove()
        setSendEnabled(true)
        wsReady = true
      } else if (data.event === 'chatResponse') {
        if (!currentAiMsg) {
          currentAiMsg = appendMsg('ai', '')
          currentAiMsg.classList.add('streaming')
        }
        if (data.done) {
          currentAiMsg.classList.remove('streaming')
          currentAiMsg = null
          setSendEnabled(true)
        } else {
          currentAiMsg.textContent += data.text
          chatMessages.scrollTop = chatMessages.scrollHeight
        }
      } else if (data.event === 'error') {
        if (currentAiMsg) {
          currentAiMsg.classList.remove('streaming')
          currentAiMsg = null
        }
        appendMsg('ai', 'Error: ' + (data.message || 'unknown'))
        setSendEnabled(true)
      }
    }

    ws.onclose = () => {
      wsReady = false
      setSendEnabled(false)
      if (currentAiMsg) {
        currentAiMsg.classList.remove('streaming')
        currentAiMsg = null
      }
      appendStatus('Disconnected... reconnecting…')
      setTimeout(connectWs, 3000)
    }

    ws.onerror = () => ws.close()
  }

  function sendMessage() {
    const text = chatInput.value.trim()
    if (!text || !wsReady) return
    appendMsg('user', text)
    chatInput.value = ''
    setSendEnabled(false)
    currentAiMsg = null
    const node = selectedNode
      ? { id: selectedNode.id, label: selectedNode.label, type: selectedNode.type }
      : null
    ws.send(JSON.stringify({
      event: 'chat',
      workspace_root: WORKSPACE_ROOT,
      text: text,
      selected_node: node,
    }))
  }

  chatSendBtn.addEventListener('click', sendMessage)
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  })

  // ── API Key section ───────────────────────────────────
  const API_BASE       = 'http://localhost:8765'
  const apiKeySection  = document.getElementById('api-key-section')
  const apiKeyFormRow  = document.getElementById('api-key-form-row')
  const apiKeyInput    = document.getElementById('api-key-input')
  const apiKeySaveBtn  = document.getElementById('api-key-save-btn')
  const apiKeyStatus   = document.getElementById('api-key-status')
  const apiKeyToggleBtn = document.getElementById('api-key-toggle-btn')

  function setKeyFormVisible(visible) {
    apiKeyFormRow.style.display = visible ? 'flex' : 'none'
    apiKeyToggleBtn.textContent = visible ? '▲' : '▼'
  }

  async function loadApiKeyStatus() {
    try {
      const res = await fetch(API_BASE + '/settings/api-key')
      const data = await res.json()
      if (data.api_key_set) {
        apiKeyStatus.textContent = 'API key is set'
        setKeyFormVisible(false)
      } else {
        apiKeyStatus.textContent = 'No API key! Enter one to enable chat'
        setKeyFormVisible(true)
      }
    } catch {
      apiKeyStatus.textContent = ''
    }
  }

  apiKeyToggleBtn.addEventListener('click', () => {
    setKeyFormVisible(apiKeyFormRow.style.display === 'none')
  })

  apiKeySaveBtn.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim()
    if (!key) return
    apiKeySaveBtn.disabled = true
    apiKeyStatus.textContent = 'Saving…'
    try {
      const res = await fetch(API_BASE + '/settings/api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key }),
      })
      if (res.ok) {
        apiKeyInput.value = ''
        apiKeyStatus.textContent = 'API key saved'
        setKeyFormVisible(false)
      } else {
        apiKeyStatus.textContent = 'Failed to save key'
      }
    } catch {
      apiKeyStatus.textContent = 'Error: is the server running?'
    } finally {
      apiKeySaveBtn.disabled = false
    }
  })

  apiKeyInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') apiKeySaveBtn.click()
  })

  loadApiKeyStatus()

  setSendEnabled(false)
  connectWs()
})()
</script>
</body>
</html>`
  }
}
