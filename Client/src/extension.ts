import * as vscode from 'vscode'
import * as path from 'path'
import { GraphPanel } from './graphTab/graphPanel'
import { VulnManagerPanel } from './vulnTab/vulnManagerPanel'
import { McpSetupPanel } from './mcpSetupTab/mcpSetupPanel'
import { getOrBuildGraph } from './graphTab/graphGenerator'
import { startSidecar, stopSidecar } from './services/sidecarManager'
import { log, disposeLogger } from './utils/logger'

export function activate(context: vscode.ExtensionContext): void {
  log('Vivian activated')

  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100)
  statusBarItem.command = 'vivian.openGraph'
  statusBarItem.text = '$(telescope) Vivian'
  statusBarItem.tooltip = 'Open Vivian Code Graph'
  statusBarItem.show()

  context.subscriptions.push(
    statusBarItem,
    vscode.commands.registerCommand('vivian.openGraph', () => openGraph(context, false)),
    vscode.commands.registerCommand('vivian.openVulnManager', () => {
      VulnManagerPanel.create(context)
    }),
    vscode.commands.registerCommand('vivian.copyMcpConfig', (type?: 'extension' | 'development') => copyMcpConfig(context, type)),
    vscode.commands.registerCommand('vivian.openMcpSetup', () => {
      McpSetupPanel.createOrShow(context)
    })
  )
}

async function copyMcpConfig(context: vscode.ExtensionContext, type?: 'extension' | 'development'): Promise<void> {
  const isWindows = process.platform === 'win32'
  
  let basePath = context.extensionPath
  if (type === 'development') {
    const workspaceFolders = vscode.workspace.workspaceFolders
    if (workspaceFolders && workspaceFolders.length > 0) {
      basePath = workspaceFolders[0].uri.fsPath
    }
  }

  const pythonPath = isWindows
    ? path.join(basePath, 'Server', 'venv', 'Scripts', 'python.exe')
    : path.join(basePath, 'Server', 'venv', 'bin', 'python')
  
  const scriptPath = path.join(basePath, 'Server', 'mcp_server.py')
  
  const config = {
    mcpServers: {
      "vivian-graph": {
        command: pythonPath,
        args: [scriptPath],
        env: {}
      }
    }
  }

  await vscode.env.clipboard.writeText(JSON.stringify(config, null, 2))
  vscode.window.showInformationMessage(`Vivian: MCP Configuration (${type === 'development' ? 'Development Mode' : 'Extension Mode'}) copied to clipboard!`)
}

async function openGraph(context: vscode.ExtensionContext, forceRebuild: boolean): Promise<void> {
  const workspaceRoot = await pickWorkspaceRoot()
  if (!workspaceRoot) return

  const config = vscode.workspace.getConfiguration('vivian')
  const autoStart: boolean = config.get('autoStartSidecar') ?? true

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'Vivian',
      cancellable: false,
    },
    async (progress) => {
      try {
        if (autoStart) {
          progress.report({ message: 'Starting sidecar…' })
          await startSidecar(context.extensionPath)
        }

        progress.report({ message: forceRebuild ? 'Rebuilding graph…' : 'Loading graph…' })
        const graph = await getOrBuildGraph(workspaceRoot, forceRebuild)

        GraphPanel.create(context, graph, workspaceRoot)
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        log(`Error: ${msg}`)
        vscode.window.showErrorMessage(`Vivian: ${msg}`)
      }
    }
  )
}

async function pickWorkspaceRoot(): Promise<string | undefined> {
  const folders = vscode.workspace.workspaceFolders
  if (!folders?.length) {
    vscode.window.showErrorMessage('Vivian: No workspace folder open.')
    return undefined
  }
  if (folders.length === 1) return folders[0].uri.fsPath

  const items = folders.map((f) => ({ label: f.name, detail: f.uri.fsPath, uri: f.uri }))
  const pick = await vscode.window.showQuickPick(items, { placeHolder: 'Select workspace root' })
  return pick?.uri.fsPath
}

export function deactivate(): void {
  stopSidecar()
  disposeLogger()
}
