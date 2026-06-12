import * as vscode from 'vscode'
import * as cp from 'child_process'
import * as path from 'path'
import { log } from '../utils/logger'

let sidecarProcess: cp.ChildProcess | undefined

// Candidates in priority order; 'py' is the Windows launcher that works even
// when 'python' and 'python3' are not on PATH.
const PYTHON_CANDIDATES = ['python', 'python3', 'py']

async function resolvePython(): Promise<string> {
  for (const cmd of PYTHON_CANDIDATES) {
    try {
      await new Promise<void>((resolve, reject) => {
        const p = cp.spawn(cmd, ['--version'], { shell: process.platform === 'win32' })
        p.on('error', reject)
        p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`exit ${code}`))))
      })
      log(`Python found: ${cmd}`)
      return cmd
    } catch {
      // try next
    }
  }
  throw new Error(
    'Python not found. Install Python 3 and ensure it is on your PATH, then reload VSCode.'
  )
}

export async function startSidecar(extensionPath: string): Promise<void> {
  if (sidecarProcess) return

  const config = vscode.workspace.getConfiguration('vivian')
  const port: number = config.get('sidecarPort') ?? 8765
  const serverPath = path.resolve(extensionPath, '..', 'Server')
  const healthUrl = `http://127.0.0.1:${port}/health`

  log(`Starting sidecar on port ${port} from ${serverPath}`)

  const python = await resolvePython()
  const stderrLines: string[] = []
  let exited = false
  let exitCode: number | null = null

  sidecarProcess = cp.spawn(
    python,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(port)],
    { cwd: serverPath, env: { ...process.env }, shell: process.platform === 'win32' }
  )

  sidecarProcess.stdout?.on('data', (d: Buffer) => log(`[sidecar] ${d.toString().trim()}`))
  sidecarProcess.stderr?.on('data', (d: Buffer) => {
    const line = d.toString().trim()
    log(`[sidecar] ${line}`)
    stderrLines.push(line)
  })
  sidecarProcess.on('exit', (code) => {
    exited = true
    exitCode = code
    log(`Sidecar exited (code ${code})`)
    sidecarProcess = undefined
  })

  await waitForHealth(healthUrl, () => {
    if (exited) {
      const tail = stderrLines.slice(-8).join('\n')
      throw new Error(
        `Sidecar process exited (code ${exitCode}) before health check passed.\n\n` +
          (tail ? `Last output:\n${tail}\n\n` : '') +
          'Make sure all Python dependencies are installed:\n  pip install -r Server/requirements.txt'
      )
    }
  })
}

async function waitForHealth(
  healthUrl: string,
  checkExit: () => void,
  retries = 40,
  delayMs = 500
): Promise<void> {
  for (let i = 0; i < retries; i++) {
    checkExit()
    try {
      const res = await fetch(healthUrl)
      if (res.ok) {
        log('Sidecar is healthy')
        return
      }
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, delayMs))
  }
  checkExit()
  throw new Error(
    `Sidecar did not respond at ${healthUrl} after ${(retries * delayMs) / 1000}s.\n` +
      'Check the Vivian output channel for details.'
  )
}

export function stopSidecar(): void {
  if (sidecarProcess) {
    sidecarProcess.kill()
    sidecarProcess = undefined
    log('Sidecar stopped')
  }
}

export function isSidecarRunning(): boolean {
  return sidecarProcess !== undefined
}
