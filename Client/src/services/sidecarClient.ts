import { KnowledgeGraph } from '../types'
import { GRAPH_BUILD_URL, GRAPH_BUILD_STATUS_URL, GRAPH_CACHE_URL } from '../utils/constants'

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 5 * 60 * 1000 // 5 minutes max

export async function buildGraph(workspaceRoot: string, cache = true): Promise<KnowledgeGraph> {
  const startRes = await fetch(GRAPH_BUILD_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot, cache }),
  })
  if (!startRes.ok) {
    throw new Error(`Graph build kick-off failed: ${startRes.status} ${startRes.statusText}`)
  }

  const statusUrl = `${GRAPH_BUILD_STATUS_URL}?workspace_root=${encodeURIComponent(workspaceRoot)}`
  const deadline = Date.now() + POLL_TIMEOUT_MS

  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS))

    const pollRes = await fetch(statusUrl)
    if (!pollRes.ok) continue

    const { status, error } = (await pollRes.json()) as { status: string; error: string | null }

    if (status === 'done') {
      const graph = await loadCacheFromServer(workspaceRoot)
      if (!graph) throw new Error('Build reported done but cache could not be loaded.')
      return graph
    }

    if (status === 'error') {
      throw new Error(`Graph build failed on server: ${error ?? 'unknown error'}`)
    }
  }

  throw new Error('Graph build timed out after 5 minutes.')
}

export async function loadCacheFromServer(workspaceRoot: string): Promise<KnowledgeGraph | null> {
  try {
    const res = await fetch(GRAPH_CACHE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_root: workspaceRoot }),
    })
    if (!res.ok) return null
    const data = (await res.json()) as KnowledgeGraph & { cached?: boolean }
    if (data.cached === false) return null
    return data
  } catch {
    return null
  }
}
