import * as vscode from 'vscode'

export class VulnManagerPanel {
  static current: VulnManagerPanel | undefined
  private readonly panel: vscode.WebviewPanel
  private disposables: vscode.Disposable[] = []

  static create(context: vscode.ExtensionContext): VulnManagerPanel {
    if (VulnManagerPanel.current) {
      VulnManagerPanel.current.panel.reveal(vscode.ViewColumn.One)
      return VulnManagerPanel.current
    }
    const panel = vscode.window.createWebviewPanel(
      'vivianVulnManager',
      'Vivian — Vulnerability Manager',
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'out')],
      }
    )
    VulnManagerPanel.current = new VulnManagerPanel(panel, context)
    return VulnManagerPanel.current
  }

  private constructor(
    panel: vscode.WebviewPanel,
    private readonly context: vscode.ExtensionContext
  ) {
    this.panel = panel
    this.panel.webview.html = this.getHtml()
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables)
    this.panel.webview.onDidReceiveMessage((msg) => this.onMessage(msg), null, this.disposables)
  }

  private onMessage(msg: any): void {
    if (msg.command === 'log') {
      console.log(`[VulnManager] ${msg.text}`)
    }
  }

  dispose(): void {
    VulnManagerPanel.current = undefined
    this.panel.dispose()
    this.disposables.forEach((d) => d.dispose())
    this.disposables = []
  }

  private getHtml(): string {
    const webview = this.panel.webview
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, 'out', 'vulnManager.js'))
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, 'out', 'vulnManager.css'))

    const nonce = getNonce()

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; font-src ${webview.cspSource};">
<title>Vivian — Vulnerability Manager</title>
<link href="${styleUri}" rel="stylesheet">
</head>
<body>
<div id="root"></div>
<script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`
  }
}

function getNonce(): string {
  let text = ''
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  for (let i = 0; i < 32; i++) text += chars.charAt(Math.floor(Math.random() * chars.length))
  return text
}
