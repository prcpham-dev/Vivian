import * as vscode from 'vscode'
import * as path from 'path'
import { GraphPanel } from './graphPanel'
import { VulnManagerPanel } from './vulnManagerPanel'
import { getOrBuildGraph } from './graphGenerator'
import { hasGraphFile } from './cacheManager'
import { startSidecar, stopSidecar } from './services/sidecarManager'
import { log, disposeLogger } from './utils/logger'

export function activate(context: vscode.ExtensionContext): void {
  log('Vivian activated')

  context.subscriptions.push(
    vscode.commands.registerCommand('vivian.openGraph', () => openGraph(context, false)),
    vscode.commands.registerCommand('vivian.openVulnManager', () => {
      VulnManagerPanel.create(context)
    })
  )
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
        const localGraphAvailable = hasGraphFile(workspaceRoot)

        if (autoStart && !localGraphAvailable) {
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
