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
            await vscode.commands.executeCommand('vivian.copyMcpConfig')
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
    const cssPath = path.join(extensionPath, 'Client', 'src', 'mcpSetupTab', 'ui', 'style.css')
    const htmlPath = path.join(extensionPath, 'Client', 'src', 'mcpSetupTab', 'ui', 'index.html')

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

  public dispose() {
    McpSetupPanel.currentPanel = undefined
    this._panel.dispose()
    while (this._disposables.length) {
      const x = this._disposables.pop()
      if (x) x.dispose()
    }
  }
}
