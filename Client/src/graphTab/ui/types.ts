export interface GraphNode {
  id: string
  label: string
  properties: any
}

export interface GraphRelationship {
  id: string
  sourceId: string
  targetId: string
  type: string
  properties?: any
}

export interface GraphData {
  nodes: GraphNode[]
  relationships: GraphRelationship[]
}

export interface D3Node {
  id: string
  label: string
  name: string
  filePath: string
  functions: any[]
  classes: any[]
  interfaces: any[]
  r: number
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

export interface D3Link {
  source: any
  target: any
  type: string
  id: string
}
