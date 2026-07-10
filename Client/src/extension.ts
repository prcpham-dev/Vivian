import * as vscode from 'vscode'
import * as path from 'path'
import * as fs from 'fs'
import { GraphPanel } from './graphTab/graphPanel'
import { VulnManagerPanel } from './vulnTab/vulnManagerPanel'
import { McpSetupPanel } from './mcpSetupTab/mcpSetupPanel'
import { getOrBuildGraph } from './graphTab/graphGenerator'
import { startSidecar, stopSidecar } from './services/sidecarManager'
import { log, disposeLogger } from './utils/logger'

export function activate(context: vscode.ExtensionContext): void {
  log('Vivian activated')

  const folders = vscode.workspace.workspaceFolders
  if (folders) {
    for (const folder of folders) {
      ensureAgentRules(folder.uri.fsPath)
    }
  }

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

  ensureAgentRules(workspaceRoot)

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

function ensureAgentRules(workspaceRoot: string): void {
  try {
    const agentsDir = path.join(workspaceRoot, '.agents')
    const agentsFile = path.join(agentsDir, 'AGENTS.md')

    if (!fs.existsSync(agentsDir)) {
      fs.mkdirSync(agentsDir, { recursive: true })
    }

    const ruleContent = `# Vivian Agent Rules

This file defines workspace-scoped behavior rules for agentic AI assistants (like Antigravity) pair-programming on this repository.

## Vivian MCP Server Permissions

The workspace is analyzed using Vivian's custom structural code graph MCP server, configured as \`vivian-graph\`.

1. **Checking Permissions**: At the start of a session, check if you have permissions to call tools under \`mcp(vivian-graph/*)\`.
2. **Proactive Request**: If permission to run these MCP tools is not already granted or is missing from your tool declarations, you MUST immediately call the \`ask_permission\` tool:
   - **Action**: \`mcp\`
   - **Target**: \`vivian-graph/*\`
   - **Reason**: Requesting access to Vivian's structural code graph tools to run auto-scan, trace functions, find symbols, and retrieve workspace statistics.
3. **Usage Priority**: Once authorized, prioritize using the Vivian graph tools (e.g., \`watch_workspace\`, \`get_workspace_graph\`, \`find_symbol\`, \`get_callers\`) over blind file reading or generic \`grep_search\` to understand codebase relationships.
`

    fs.writeFileSync(agentsFile, ruleContent, 'utf8')
    log(`Agent rules ensured at ${agentsFile}`)
  } catch (err) {
    log(`Failed to write agent rules: ${err}`)
  }
}
