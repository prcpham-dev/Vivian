import { KnowledgeGraph } from '../types'
import { buildGraph } from '../services/sidecarClient'
import { log } from '../utils/logger'

export async function getOrBuildGraph(workspaceRoot: string, forceRebuild = false): Promise<KnowledgeGraph> {
  log('Building graph via server...')
  const graph = await buildGraph(workspaceRoot, !forceRebuild)
  log(`Graph built: ${graph.nodes?.length ?? 0} nodes, ${graph.relationships?.length ?? 0} relationships`)
  return graph
}
