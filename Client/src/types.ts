export type NodeLabel = 'File' | 'Folder' | 'Class' | 'Function' | 'Interface' | 'Struct' | 'Enum' | 'Record'
export type RelationshipType = 'CONTAINS' | 'IMPORTS' | 'CALLS' | 'INHERITS'

export interface FunctionDef {
  name: string
  params?: string
  returnType?: string
  line?: number
  calledBy?: string[]
  calls?: string[]
}

export interface ClassDef {
  name: string
  extends?: string[]
  line?: number
}

export interface InterfaceDef {
  name: string
  extends?: string[]
  line?: number
}

export interface NodeProperties {
  name: string
  filePath?: string
  functions?: FunctionDef[]
  classes?: ClassDef[]
  interfaces?: InterfaceDef[]
  line?: number
}

export interface GraphNode {
  id: string
  label: NodeLabel
  properties: NodeProperties
}

export interface GraphRelationship {
  id: string
  type: RelationshipType
  sourceId: string
  targetId: string
  confidence: number
  reason: string
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  relationships: GraphRelationship[]
  timestamp: number
}

export interface WebViewMessage {
  command: string
  [key: string]: unknown
}
