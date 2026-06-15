import { GraphData, D3Node, D3Link } from './types'
import { vscode } from './api'

// ── Constants ────────────────────────────────────────
const NODE_COLORS: Record<string, string> = {
  File:      '#4FC3F7',
  Folder:    '#78909C',
  Class:     '#FFB74D',
  Function:  '#81C784',
  Interface: '#CE93D8',
  Struct:    '#F48FB1',
  Enum:      '#80CBC4',
  Record:    '#A5D6A7',
}

const LINK_COLORS: Record<string, string> = {
  IMPORTS:  '#64B5F6',
  CONTAINS: '#607D8B',
  CALLS:    '#FFD54F',
  INHERITS: '#CE93D8',
}

const NODE_RADII: Record<string, number> = {
  File:      9,
  Folder:    11,
  Class:     8,
  Function:  6,
  Interface: 7,
  Struct:    7,
  Enum:      6,
  Record:    6,
}

// ── State ────────────────────────────────────────────
let graphData: GraphData | null = null
let activeRelTypes  = new Set(['IMPORTS', 'CALLS', 'INHERITS', 'CONTAINS'])
let activeNodeTypes = new Set(['File', 'Folder', 'Class', 'Function', 'Interface', 'Struct', 'Enum', 'Record'])
let selectedNode: D3Node | null = null
let simulation: any = null

export function getSelectedNode() {
  return selectedNode
}

let svg: any, rootG: any, linksG: any, nodesG: any, arrowG: any, zoom: any

export function initGraph() {
  svg     = d3.select('#svg')
  rootG   = svg.append('g')
  linksG  = rootG.append('g').attr('class', 'links-layer')
  nodesG  = rootG.append('g').attr('class', 'nodes-layer')
  arrowG  = svg.append('defs')

  // Arrow marker per relationship type
  Object.entries(LINK_COLORS).forEach(([type, color]) => {
    arrowG.append('marker')
      .attr('id', 'arrow-' + type)
      .attr('viewBox', '0 -4 8 8')
      .attr('refX', 18)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', color as string)
        .attr('opacity', 0.6)
  })

  zoom = d3.zoom()
    .scaleExtent([0.05, 4])
    .on('zoom', (event: any) => rootG.attr('transform', event.transform))

  svg.call(zoom)
  svg.on('dblclick.zoom', null)
  svg.on('click', (event: any) => {
    if (event.target === svg.node() || event.target.tagName === 'svg') clearSelection()
  })

  // ── Search ───────────────────────────────────────────
  document.getElementById('search')!.addEventListener('input', applyFilters)
  document.getElementById('search')!.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { (e.target as HTMLInputElement).value = ''; applyFilters() }
  })

  // ── Keyboard shortcuts ────────────────────────────────
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') clearSelection()
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault()
      document.getElementById('search')!.focus()
    }
  })

  document.getElementById('close-panel-btn')!.addEventListener('click', clearSelection)
}

export function renderGraph(data: GraphData) {
  graphData = data
  document.getElementById('loading')!.style.display = 'none'

  buildFilterChips()

  const validIds = new Set(data.nodes.map(n => n.id))

  // Build D3 node/link arrays
  const nodes: D3Node[] = data.nodes.map(n => ({
    id: n.id,
    label: n.label,
    name: n.properties.name,
    filePath: n.properties.filePath,
    functions: n.properties.functions || [],
    classes: n.properties.classes || [],
    interfaces: n.properties.interfaces || [],
    r: NODE_RADII[n.label as string] || 7,
  }))

  const links: D3Link[] = data.relationships
    .filter(r => validIds.has(r.sourceId) && validIds.has(r.targetId))
    .map(r => ({
      source: r.sourceId,
      target: r.targetId,
      type:   r.type,
      id:     r.id,
    }))

  // Destroy old simulation
  if (simulation) simulation.stop()

  const { width, height } = document.getElementById('svg')!.getBoundingClientRect()
  const cx = width  / 2 || 600
  const cy = height / 2 || 400

  simulation = d3.forceSimulation(nodes)
    .force('link',      d3.forceLink(links).id((d: any) => d.id).distance((d: any) => d.type === 'CONTAINS' ? 60 : 120))
    .force('charge',    d3.forceManyBody().strength((d: any) => d.label === 'File' ? -350 : -150))
    .force('center',    d3.forceCenter(cx, cy))
    .force('collision', d3.forceCollide((d: any) => d.r + 4))
    .force('x',         d3.forceX(cx).strength(0.04))
    .force('y',         d3.forceY(cy).strength(0.04))
    .alphaDecay(0.03)

  // ── Links ────────────────────────────
  const link = linksG.selectAll('.link')
    .data(links, (d: any) => d.id)
    .join('line')
      .attr('class', (d: any) => 'link ' + d.type)
      .attr('marker-end', (d: any) => `url(#arrow-${d.type})`)

  // ── Nodes ────────────────────────────
  const node = nodesG.selectAll('.node')
    .data(nodes, (d: any) => d.id)
    .join('g')
      .attr('class', 'node')
      .call(d3.drag()
        .on('start', dragStart)
        .on('drag',  dragged)
        .on('end',   dragEnd))
      .on('click', (event: any, d: any) => { event.stopPropagation(); selectNode(d, node, link) })
      .on('mouseover', showTooltip)
      .on('mousemove', moveTooltip)
      .on('mouseout',  hideTooltip)

  node.append('circle').attr('r', (d: any) => d.r).attr('fill', (d: any) => NODE_COLORS[d.label] || '#aaa')
  node.append('text').attr('dy', (d: any) => d.r + 10).attr('class', 'label-text').text((d: any) => truncate(d.name, 18))

  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => clamp(d.target)).attr('y2', (d: any) => clampY(d.target))

    node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
  })

  document.getElementById('node-count')!.textContent =
    `${nodes.length} nodes · ${links.length} edges`

  applyFilters()
}

// ── Build filter chips ────────────────────────────────
function buildFilterChips() {
  const relContainer  = document.getElementById('rel-filters')!
  const nodeContainer = document.getElementById('node-filters')!

  // Clear old chips (keep the label spans)
  Array.from(relContainer.querySelectorAll('.chip')).forEach(e => e.remove())
  Array.from(nodeContainer.querySelectorAll('.chip')).forEach(e => e.remove())

  if(!graphData) return;

  // Relationship chips
  const relTypes = [...new Set(graphData.relationships.map(r => r.type))] as string[]
  relTypes.forEach(type => {
    const chip = document.createElement('span')
    chip.className = 'chip active'
    chip.style.color = LINK_COLORS[type] || '#aaa'
    chip.innerHTML = `<span class="chip-dot" style="background:${LINK_COLORS[type] || '#aaa'}"></span>${type}`
    chip.dataset.type = type
    chip.addEventListener('click', () => {
      if (activeRelTypes.has(type)) activeRelTypes.delete(type)
      else activeRelTypes.add(type)
      chip.classList.toggle('active')
      applyFilters()
    })
    relContainer.appendChild(chip)
  })

  // Node type chips
  const nodeTypes = [...new Set(graphData.nodes.map(n => n.label))] as string[]
  nodeTypes.forEach(type => {
    const chip = document.createElement('span')
    chip.className = 'chip active'
    chip.style.color = NODE_COLORS[type] || '#aaa'
    chip.innerHTML = `<span class="chip-dot" style="background:${NODE_COLORS[type] || '#aaa'}"></span>${type}`
    chip.dataset.type = type
    chip.addEventListener('click', () => {
      if (activeNodeTypes.has(type)) activeNodeTypes.delete(type)
      else activeNodeTypes.add(type)
      chip.classList.toggle('active')
      applyFilters()
    })
    nodeContainer.appendChild(chip)
  })
}

// Push links back so they don't overlap the node center
function clamp(d: any) {
  return d.x
}
function clampY(d: any) {
  return d.y
}

// ── Filters ───────────────────────────────────────────
function applyFilters() {
  if (!graphData) return
  const searchTerm = (document.getElementById('search') as HTMLInputElement).value.trim().toLowerCase()
  const visibleNodeIds = new Set(
    graphData.nodes
      .filter(n => activeNodeTypes.has(n.label))
      .map(n => n.id)
  )

  linksG.selectAll('.link').style('display', (d: any) =>
    activeRelTypes.has(d.type) &&
    visibleNodeIds.has(typeof d.source === 'object' ? d.source.id : d.source) &&
    visibleNodeIds.has(typeof d.target === 'object' ? d.target.id : d.target)
      ? null
      : 'none'
  )

  nodesG.selectAll('.node').style('display', (d: any) =>
    activeNodeTypes.has(d.label) ? null : 'none'
  )

  if (searchTerm) {
    const matched = new Set()
    nodesG.selectAll('.node').each((d: any) => {
      if (d.name.toLowerCase().includes(searchTerm) || d.id.toLowerCase().includes(searchTerm)) {
        matched.add(d.id)
      }
    })

    nodesG.selectAll('.node')
      .classed('dimmed', (d: any) => !matched.has(d.id))

    if (matched.size > 0) {
      const first = nodesG.selectAll('.node').filter((d: any) => matched.has(d.id)).datum()
      if (first) panToNode(first)
    }
  } else {
    nodesG.selectAll('.node').classed('dimmed', false)
  }
}

// ── Selection ────────────────────────────────────────
let nodesSel: any = null

function selectNode(d: any, nodeSel: any, linkSel: any) {
  selectedNode = d
  nodesSel = nodesSel || nodesG.selectAll('.node')
  const linksSel = linksG.selectAll('.link')

  nodesG.selectAll('.node').classed('selected', (n: any) => n.id === d.id)

  const connectedIds = new Set([d.id])
  linksSel.each((l: any) => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source
    const tid = typeof l.target === 'object' ? l.target.id : l.target
    if (sid === d.id || tid === d.id) {
      connectedIds.add(sid)
      connectedIds.add(tid)
    }
  })

  nodesG.selectAll('.node').classed('dimmed', (n: any) => !connectedIds.has(n.id))
  linksSel
    .classed('highlighted', (l: any) => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source
      const tid = typeof l.target === 'object' ? l.target.id : l.target
      return sid === d.id || tid === d.id
    })

  showInfoPanel(d)
}

function clearSelection() {
  selectedNode = null
  nodesG.selectAll('.node').classed('selected', false).classed('dimmed', false)
  linksG.selectAll('.link').classed('highlighted', false)
  document.getElementById('info-panel')!.classList.remove('visible')
}

// ── Info panel ────────────────────────────────────────
function showInfoPanel(d: any) {
  const panel = document.getElementById('info-panel')!
  panel.classList.add('visible')

  document.getElementById('info-name')!.textContent = d.name
  const badge = document.getElementById('info-badge')!
  badge.textContent = d.label
  badge.style.background = (NODE_COLORS[d.label] || '#888') + '33'
  badge.style.color = NODE_COLORS[d.label] || '#888'

  const pathEl = document.getElementById('info-path')!
  pathEl.textContent = d.filePath || d.id

  const openBtn = document.getElementById('open-file-btn')!
  openBtn.style.display = (d.label === 'File') ? 'block' : 'none'
  openBtn.onclick = () => vscode.postMessage({ command: 'openFile', filePath: d.filePath || d.id })

  // Functions
  const funcEl = document.getElementById('info-functions')!
  if (d.functions && d.functions.length) {
    funcEl.innerHTML = `<div class="section-title">Functions (${d.functions.length})</div>` +
      d.functions.map((f: any) => `<div class="func-item" title="${f.name}">${f.name}${f.params ? '(' + f.params + ')' : '()'}${f.returnType ? ': ' + f.returnType : ''}</div>`).join('')
  } else {
    funcEl.innerHTML = ''
  }

  // Connected nodes
  const importsEl = document.getElementById('info-imports')!
  const importedByEl = document.getElementById('info-imported-by')!

  if (!graphData) return

  const visibleNodeIds = new Set(
    graphData.nodes
      .filter(n => activeNodeTypes.has(n.label))
      .map(n => n.id)
  )

  const outgoing = graphData.relationships.filter(r => {
    const sid = r.sourceId
    return sid === d.id && activeRelTypes.has(r.type) && visibleNodeIds.has(r.targetId)
  })
  const incoming = graphData.relationships.filter(r => {
    const tid = r.targetId
    return tid === d.id && activeRelTypes.has(r.type) && visibleNodeIds.has(r.sourceId)
  })

  const nodeNameMap = new Map(graphData.nodes.map(n => [n.id, n.properties.name]))

  if (outgoing.length) {
    importsEl.innerHTML = `<div class="section-title">References (${outgoing.length})</div>` +
      outgoing.map((r: any) => `<div class="rel-item" data-id="${r.targetId}">${r.type} → ${nodeNameMap.get(r.targetId) || r.targetId}</div>`).join('')
  } else {
    importsEl.innerHTML = ''
  }

  if (incoming.length) {
    importedByEl.innerHTML = `<div class="section-title">Referenced by (${incoming.length})</div>` +
      incoming.map((r: any) => `<div class="rel-item" data-id="${r.sourceId}">${r.type} ← ${nodeNameMap.get(r.sourceId) || r.sourceId}</div>`).join('')
  } else {
    importedByEl.innerHTML = ''
  }

  // Click to pan to related node
  panel.querySelectorAll('.rel-item').forEach(el => {
    el.addEventListener('click', () => {
      const targetId = (el as HTMLElement).dataset.id
      const targetDatum = nodesG.selectAll('.node').filter((n: any) => n.id === targetId).datum()
      if (targetDatum) panToNode(targetDatum)
    })
  })
}

// ── Pan to node ───────────────────────────────────────
function panToNode(d: any) {
  const svgEl = document.getElementById('svg')!
  const { width, height } = svgEl.getBoundingClientRect()
  const scale = 1.2
  const tx = width / 2 - scale * d.x
  const ty = height / 2 - scale * d.y
  svg.transition().duration(600)
    .call(zoom.transform as any, d3.zoomIdentity.translate(tx, ty).scale(scale))
}

// ── Drag ─────────────────────────────────────────────
function dragStart(event: any, d: any) {
  if (!event.active) simulation.alphaTarget(0.3).restart()
  d.fx = d.x; d.fy = d.y
}
function dragged(event: any, d: any) {
  d.fx = event.x; d.fy = event.y
}
function dragEnd(event: any, d: any) {
  if (!event.active) simulation.alphaTarget(0)
  d.fx = null; d.fy = null
}

// ── Tooltip ──────────────────────────────────────────
function showTooltip(event: any, d: any) {
  const tooltip = document.getElementById('tooltip')!
  const fCount = (d.functions || []).length
  const cCount = (d.classes   || []).length
  tooltip.innerHTML = `<strong>${d.name}</strong><br><span style="color:#888">${d.label}</span>` +
    (fCount ? `<br>${fCount} function${fCount === 1 ? '' : 's'}` : '') +
    (cCount ? `<br>${cCount} class${cCount === 1 ? '' : 'es'}` : '') +
    `<br><span style="color:#888;font-size:10px">${d.id}</span>`
  tooltip.classList.add('visible')
  moveTooltip(event)
}
function moveTooltip(event: any) {
  const tooltip = document.getElementById('tooltip')!
  tooltip.style.left = (event.clientX + 14) + 'px'
  tooltip.style.top  = (event.clientY - 10) + 'px'
}
function hideTooltip() {
  const tooltip = document.getElementById('tooltip')!
  tooltip.classList.remove('visible')
}

// ── Helpers ──────────────────────────────────────────
function truncate(str: string, max: number) {
  return str && str.length > max ? str.slice(0, max - 1) + '…' : (str || '')
}
