import * as vscode from 'vscode'
import * as cp from 'child_process'
import * as path from 'path'
import * as fs from 'fs'
import * as net from 'net'
import { log } from '../utils/logger'

let sidecarProcess: cp.ChildProcess | undefined
let activePort: number | undefined

/** Returns the port the sidecar is currently running on. */
export function getActivePort(): number {
  return activePort ?? 8765
}

/** Find an available TCP port, preferring `preferred` but falling back to any free one. */
function findFreePort(preferred: number): Promise<number> {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.listen(preferred, '127.0.0.1', () => {
      const addr = server.address() as net.AddressInfo
      server.close(() => resolve(addr.port))
    })
    server.on('error', () => {
      // preferred port busy — let OS assign a free one
      const fallback = net.createServer()
      fallback.listen(0, '127.0.0.1', () => {
        const addr = fallback.address() as net.AddressInfo
        fallback.close(() => resolve(addr.port))
      })
    })
  })
}

const PYTHON_CANDIDATES = ['python', 'python3', 'py']

async function resolvePython(serverPath: string): Promise<string> {
  const rootPath = path.join(serverPath, '..')
  const venvPaths = [
    path.join(serverPath, 'venv', 'bin', 'python'),
    path.join(serverPath, 'venv', 'Scripts', 'python.exe'),
    path.join(serverPath, '.venv', 'bin', 'python'),
    path.join(serverPath, '.venv', 'Scripts', 'python.exe'),
    path.join(rootPath, 'venv', 'bin', 'python'),
    path.join(rootPath, 'venv', 'Scripts', 'python.exe'),
    path.join(rootPath, '.venv', 'bin', 'python'),
    path.join(rootPath, '.venv', 'Scripts', 'python.exe'),
  ]

  for (const venvPath of venvPaths) {
    if (fs.existsSync(venvPath)) {
      log(`Python found in venv: ${venvPath}`)
      return venvPath
    }
  }

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

async function ensureDependencies(serverPath: string): Promise<string> {
  let pythonPath = await resolvePython(serverPath)
  const rootPath = path.join(serverPath, '..')

  // If the resolved python is not inside the workspace (i.e. it's a global python),
  // let's create a venv to keep things clean.
  if (!pythonPath.includes(rootPath)) {
    log(`Creating virtual environment in ${serverPath}/venv...`)
    await new Promise<void>((resolve, reject) => {
      const p = cp.spawn(pythonPath, ['-m', 'venv', 'venv'], { cwd: serverPath, shell: process.platform === 'win32' })
      p.on('error', reject)
      p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`Failed to create venv (exit ${code})`))))
    })
    // Re-resolve to get the new venv python
    pythonPath = await resolvePython(serverPath)
  }

  log(`Checking/installing dependencies using ${pythonPath}...`)
  const reqPath = path.join(serverPath, '..', 'requirements.txt')
  await new Promise<void>((resolve, reject) => {
    const p = cp.spawn(pythonPath, ['-m', 'pip', 'install', '-r', reqPath], { cwd: serverPath, shell: process.platform === 'win32' })
    p.stdout?.on('data', (d: Buffer) => log(`[pip] ${d.toString().trim()}`))
    p.stderr?.on('data', (d: Buffer) => log(`[pip] ${d.toString().trim()}`))
    p.on('error', reject)
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`pip install failed (exit ${code})`))))
  })

  return pythonPath
}

export async function startSidecar(extensionPath: string): Promise<void> {
  if (sidecarProcess) return

  const config = vscode.workspace.getConfiguration('vivian')
  const preferredPort: number = config.get('sidecarPort') ?? 8765
  const serverPath = path.join(extensionPath, 'Server')

  // If something is already listening and healthy on the preferred port, reuse it.
  const preferredHealthUrl = `http://127.0.0.1:${preferredPort}/health`
  try {
    const res = await fetch(preferredHealthUrl)
    if (res.ok) {
      const data = await res.json() as { status?: string; service?: string }
      if (data?.service === 'vivian-sidecar') {
        activePort = preferredPort
        log(`Sidecar already running on port ${preferredPort}, reusing it.`)
        return
      }
    }
  } catch {
    // nothing on that port yet — proceed to spawn
  }

  // Pick a free port (preferred first, OS-assigned fallback)
  const port = await findFreePort(preferredPort)
  activePort = port
  const healthUrl = `http://127.0.0.1:${port}/health`

  log(`Starting sidecar on port ${port} from ${serverPath}`)

  const python = await ensureDependencies(serverPath)
  const stderrLines: string[] = []
  let exited = false
  let exitCode: number | null = null

  sidecarProcess = cp.spawn(
    python,
    ['-m', 'uvicorn', 'sidecar:app', '--host', '127.0.0.1', '--port', String(port)],
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
      const portInUse = tail.includes('10048') || tail.includes('address already in use')
      if (portInUse) {
        throw new Error(
          `Port ${port} is already in use by another process.\n\n` +
          `Either close the other process or change the port in VS Code settings:\n` +
          `  vivian.sidecarPort (currently ${port})`
        )
      }
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
        const data = await res.json() as { status?: string; service?: string }
        if (data?.service === 'vivian-sidecar') {
          log('Sidecar is healthy')
          return
        }
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
