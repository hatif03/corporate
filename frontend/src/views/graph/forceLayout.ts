// A small, hand-rolled deterministic force-directed layout — Coulomb
// repulsion + Hooke spring + centre gravity + damping. Seeded by node
// index, not Math.random(), so it doesn't reshuffle every re-render; no
// external graph-layout library needed for a handful of department nodes.

export interface GraphNode {
  id: string
  degree: number
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface PositionedNode extends GraphNode {
  x: number
  y: number
}

const WIDTH = 480
const HEIGHT = 360
const ITERATIONS = 200
const REPULSION = 6000
const SPRING_LENGTH = 110
const SPRING_STRENGTH = 0.02
const DAMPING = 0.85
const GRAVITY = 0.01

export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): PositionedNode[] {
  const cx = WIDTH / 2
  const cy = HEIGHT / 2
  const positioned = nodes.map((n, i) => {
    // Deterministic seed placement: spread nodes evenly on a circle indexed
    // by their position in the input array, not random.
    const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1)
    const radius = Math.min(WIDTH, HEIGHT) / 3
    return { ...n, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle), vx: 0, vy: 0 }
  })
  const byId = new Map(positioned.map((n) => [n.id, n]))

  for (let iter = 0; iter < ITERATIONS; iter++) {
    for (const a of positioned) {
      let fx = 0
      let fy = 0

      for (const b of positioned) {
        if (a === b) continue
        const dx = a.x - b.x
        const dy = a.y - b.y
        const distSq = Math.max(dx * dx + dy * dy, 1)
        const force = REPULSION / distSq
        const dist = Math.sqrt(distSq)
        fx += (dx / dist) * force
        fy += (dy / dist) * force
      }

      fx += (cx - a.x) * GRAVITY
      fy += (cy - a.y) * GRAVITY

      a.vx = (a.vx + fx) * DAMPING
      a.vy = (a.vy + fy) * DAMPING
    }

    for (const edge of edges) {
      const source = byId.get(edge.source)
      const target = byId.get(edge.target)
      if (!source || !target) continue
      const dx = target.x - source.x
      const dy = target.y - source.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      const displacement = (dist - SPRING_LENGTH) * SPRING_STRENGTH
      const fx = (dx / dist) * displacement
      const fy = (dy / dist) * displacement
      source.vx += fx
      source.vy += fy
      target.vx -= fx
      target.vy -= fy
    }

    for (const n of positioned) {
      n.x += n.vx
      n.y += n.vy
      n.x = Math.max(30, Math.min(WIDTH - 30, n.x))
      n.y = Math.max(30, Math.min(HEIGHT - 30, n.y))
    }
  }

  return positioned.map(({ id, degree, x, y }) => ({ id, degree, x, y }))
}

export { WIDTH, HEIGHT }
