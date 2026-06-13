import { KnowledgeGraph } from './types'
import { buildGraph } from './services/sidecarClient'
import { loadCache, loadGraphFile } from './cacheManager'
import { log } from './utils/logger'

export async function getOrBuildGraph(workspaceRoot: string, forceRebuild = false): Promise<KnowledgeGraph> {
  const graphFile = loadGraphFile(workspaceRoot)
  if (graphFile) {
    log(`Loaded graph from graph.json: ${graphFile.nodes.length} nodes, ${graphFile.relationships.length} edges`)
    return graphFile
  }

  if (!forceRebuild) {
    const cached = loadCache(workspaceRoot)
    if (cached) {
      log(`Loaded graph from cache: ${cached.nodes.length} nodes, ${cached.relationships.length} edges`)
      return cached
    }
  }

  log('Building graph via sidecar...')
  const graph = await buildGraph(workspaceRoot, true)
  log(`Graph built: ${graph.nodes.length} nodes, ${graph.relationships.length} relationships`)
  return graph
}
