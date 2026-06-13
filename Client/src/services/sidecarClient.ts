import { KnowledgeGraph } from '../types'
import { GRAPH_BUILD_URL, GRAPH_CACHE_URL } from '../utils/constants'

export async function buildGraph(workspaceRoot: string, cache = true): Promise<KnowledgeGraph> {
  const res = await fetch(GRAPH_BUILD_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_root: workspaceRoot, cache }),
  })
  if (!res.ok) throw new Error(`Graph build failed: ${res.status} ${res.statusText}`)
  return res.json() as Promise<KnowledgeGraph>
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
