import { KnowledgeGraph } from './types'
import { buildGraph } from './services/sidecarClient'
import { log } from './utils/logger'

export async function getOrBuildGraph(workspaceRoot: string, forceRebuild = false): Promise<KnowledgeGraph> {
  log('Building graph via server...')
  const graph = await buildGraph(workspaceRoot, !forceRebuild)
  log(`Graph built: ${graph.nodes.length} nodes, ${graph.relationships.length} relationships`)
  return graph
}
