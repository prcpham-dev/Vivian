import * as fs from 'fs'
import * as path from 'path'
import { KnowledgeGraph } from './types'
import { CACHE_FILE_NAME, GRAPH_FILE_NAME } from './utils/constants'

function parseGraph(raw: string, source: string): KnowledgeGraph {
  let graph: unknown
  try {
    graph = JSON.parse(raw)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    throw new Error(`Invalid ${source}: ${msg}`)
  }

  if (
    !graph ||
    typeof graph !== 'object' ||
    !Array.isArray((graph as KnowledgeGraph).nodes) ||
    !Array.isArray((graph as KnowledgeGraph).relationships)
  ) {
    throw new Error(`Invalid ${source}: expected nodes and relationships arrays`)
  }

  return graph as KnowledgeGraph
}

export function graphFilePath(workspaceRoot: string): string {
  return path.join(workspaceRoot, GRAPH_FILE_NAME)
}

export function hasGraphFile(workspaceRoot: string): boolean {
  return fs.existsSync(graphFilePath(workspaceRoot))
}

export function loadGraphFile(workspaceRoot: string): KnowledgeGraph | null {
  const filePath = graphFilePath(workspaceRoot)
  if (!fs.existsSync(filePath)) return null
  return parseGraph(fs.readFileSync(filePath, 'utf-8'), GRAPH_FILE_NAME)
}

export function loadCache(workspaceRoot: string): KnowledgeGraph | null {
  const cachePath = path.join(workspaceRoot, CACHE_FILE_NAME)
  if (!fs.existsSync(cachePath)) return null
  try {
    return JSON.parse(fs.readFileSync(cachePath, 'utf-8')) as KnowledgeGraph
  } catch {
    return null
  }
}

export function saveCache(workspaceRoot: string, graph: KnowledgeGraph): void {
  const cachePath = path.join(workspaceRoot, CACHE_FILE_NAME)
  try {
    fs.writeFileSync(cachePath, JSON.stringify(graph, null, 2), 'utf-8')
  } catch {
    // ignore write failures
  }
}
