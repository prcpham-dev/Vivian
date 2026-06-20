export const vscode = acquireVsCodeApi()

// Port is injected at runtime by graphPanel.ts as window.SIDECAR_PORT
const port: number = (window as any).SIDECAR_PORT ?? 8765

export const API_BASE = `http://localhost:${port}`
export const WS_URL = `ws://localhost:${port}/ws`

export async function fetchJson(endpoint: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${endpoint}`, options)
  return res.json()
}
