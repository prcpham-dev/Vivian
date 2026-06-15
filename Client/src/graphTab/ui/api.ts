export const vscode = acquireVsCodeApi()
export const API_BASE = 'http://localhost:8765'
export const WS_URL = 'ws://localhost:8765/ws'

export async function fetchJson(endpoint: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${endpoint}`, options)
  return res.json()
}
