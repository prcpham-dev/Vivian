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

  private async onMessage(msg: any): Promise<void> {
    if (msg.command === 'log') {
      console.log(`[VulnManager] ${msg.text}`)
    } else if (msg.command === 'openGraph') {
      vscode.commands.executeCommand('vivian.openGraph')
    } else if (msg.command === 'requestFiles') {
      const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || ''
      const workspaceName = vscode.workspace.workspaceFolders?.[0]?.name || 'Workspace'
      
      if (!workspaceRoot) {
        this.panel.webview.postMessage({ command: 'filesLoaded', files: [], workspaceName })
        return
      }

      const { loadCacheFromServer } = require('./services/sidecarClient')
      loadCacheFromServer(workspaceRoot).then((graph: any) => {
        let files: string[] = []
        if (graph && graph.nodes) {
          files = graph.nodes
            .filter((n: any) => n.label === 'File' && n.properties && n.properties.filePath)
            .map((n: any) => n.properties.filePath)
        }
        this.panel.webview.postMessage({ command: 'filesLoaded', files, workspaceName, workspaceRoot })
      }).catch((e: any) => {
        console.error('Error loading graph:', e)
        this.panel.webview.postMessage({ command: 'filesLoaded', files: [], workspaceName, workspaceRoot })
      })
    } else if (msg.command === 'requestGitChanges') {
      const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
      if (!workspaceRoot) {
        this.panel.webview.postMessage({ command: 'gitChangesLoaded', files: [] })
        return
      }
      const { exec } = require('child_process')
      exec('git status --porcelain', { cwd: workspaceRoot }, (err: any, stdout: string) => {
        let files: string[] = []
        if (stdout) {
          try {
            files = stdout.split('\n')
              .filter((f: string) => f.trim() !== '')
              .map((f: string) => {
                // "XY filename" or "XY "filename with spaces""
                let file = f.substring(3).trim();
                if (file.startsWith('"') && file.endsWith('"')) {
                  file = file.slice(1, -1);
                }
                return file;
              })
          } catch (e) {
            console.error('Error parsing git status:', e)
          }
        }
        this.panel.webview.postMessage({ command: 'gitChangesLoaded', files })
      })
    } else if (msg.command === 'openDiff') {
      const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
      if (!workspaceRoot) return
      
      const filePath = msg.filePath
      const absolutePath = require('path').join(workspaceRoot, filePath)
      const fileUri = vscode.Uri.file(absolutePath)
      
      const { exec } = require('child_process')
      const os = require('os')
      const path = require('path')
      const fs = require('fs')
      
      // Fetch the HEAD version of the file
      exec(`git show HEAD:"${filePath}"`, { cwd: workspaceRoot, maxBuffer: 1024 * 1024 * 10 }, (err: any, stdout: string) => {
        if (err) {
          // Fallback: If it's an untracked file (not in HEAD), just open it normally
          vscode.commands.executeCommand('vscode.open', fileUri, { preview: true })
        } else {
          // Write the HEAD version to a temporary file
          const tempFileName = `HEAD_${path.basename(filePath)}`
          const tempFilePath = path.join(os.tmpdir(), tempFileName)
          fs.writeFileSync(tempFilePath, stdout)
          
          const headUri = vscode.Uri.file(tempFilePath)
          const title = `${path.basename(filePath)} (Working Tree)`
          
          // Open the native VS Code split-diff viewer
          vscode.commands.executeCommand('vscode.diff', headUri, fileUri, title, { preview: true }).then(() => {
            // Clean up the temp file after a short delay
            setTimeout(() => {
              try { fs.unlinkSync(tempFilePath) } catch (e) {}
            }, 5000)
          }, () => {
            // Fallback if diff fails
            vscode.commands.executeCommand('vscode.open', fileUri, { preview: true })
          })
        }
      })
    } else if (msg.command === 'requestFileContent') {
      const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
      if (!workspaceRoot) return
      try {
        const fullPath = require('path').isAbsolute(msg.filePath) ? msg.filePath : require('path').join(workspaceRoot, msg.filePath)
        const content = require('fs').readFileSync(fullPath, 'utf-8')
        this.panel.webview.postMessage({ command: 'fileContent', filePath: msg.filePath, content })
      } catch (err) {
        this.panel.webview.postMessage({ command: 'fileContent', filePath: msg.filePath, content: `Error reading file: ${err}` })
      }
    } else if (msg.command === 'getGitDiff') {
      const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
      if (!workspaceRoot) return
      const { exec } = require('child_process')
      exec('git diff', { cwd: workspaceRoot }, (err: any, stdout: string) => {
        this.panel.webview.postMessage({ command: 'gitDiffContent', diff: stdout || '' })
      })
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
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src http://localhost:* http://127.0.0.1:*; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; font-src ${webview.cspSource};">
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
