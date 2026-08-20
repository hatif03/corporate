import { useEffect, useMemo, useState } from 'react'
import { watchMessages, type MessageEntry } from '../../lib/platformClient'
import { layoutGraph, HEIGHT, WIDTH, type GraphEdge, type GraphNode } from './forceLayout'
import type { Agent } from '../../lib/types'

const ACT_COLOR: Record<string, string> = {
  request: '#4ecdc4',
  query: '#9b7ede',
  propose: '#ff9f43',
  agree: '#6bcf7f',
  done: '#6bcf7f',
  refuse: '#ff6b6b',
  inform: '#6c8ef5',
}

interface AggregatedEdge extends GraphEdge {
  lastAct: string
}

export function GraphView({ agents, orgId }: { agents: Agent[]; orgId: string }) {
  const [messages, setMessages] = useState<MessageEntry[]>([])

  useEffect(() => watchMessages(orgId, setMessages), [orgId])

  const { nodes, edges } = useMemo(() => {
    const degree: Record<string, number> = {}
    const edgeMap = new Map<string, AggregatedEdge>()

    for (const m of messages) {
      degree[m.from] = (degree[m.from] ?? 0) + 1
      degree[m.to] = (degree[m.to] ?? 0) + 1
      const key = `${m.from}->${m.to}`
      const existing = edgeMap.get(key)
      if (existing) {
        existing.weight += 1
        existing.lastAct = m.act
      } else {
        edgeMap.set(key, { source: m.from, target: m.to, weight: 1, lastAct: m.act })
      }
    }

    const nodeIds = new Set<string>([...agents.map((a) => a.id), ...Object.keys(degree)])
    const graphNodes: GraphNode[] = Array.from(nodeIds).map((id) => ({ id, degree: degree[id] ?? 0 }))

    return { nodes: graphNodes, edges: Array.from(edgeMap.values()) }
  }, [messages, agents])

  const positioned = useMemo(() => layoutGraph(nodes, edges), [nodes, edges])
  const positionById = useMemo(() => new Map(positioned.map((n) => [n.id, n])), [positioned])

  return (
    <div className="corp-panel">
      <svg width={WIDTH} height={HEIGHT} style={{ background: '#fafafa', border: '1px solid #ddd' }}>
        {edges.map((edge, i) => {
          const source = positionById.get(edge.source)
          const target = positionById.get(edge.target)
          if (!source || !target) return null
          const act = (edge as AggregatedEdge).lastAct
          return (
            <line
              key={i}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={ACT_COLOR[act] ?? '#999'}
              strokeWidth={Math.min(1 + edge.weight, 6)}
              opacity={0.7}
            />
          )
        })}
        {positioned.map((n) => {
          const agent = agents.find((a) => a.id === n.id)
          const size = 10 + Math.min(n.degree * 2, 20)
          return (
            <g key={n.id}>
              <rect
                x={n.x - size / 2}
                y={n.y - size / 2}
                width={size}
                height={size}
                fill={agent?.isCeo ? 'var(--corp-accent-lemon)' : 'var(--corp-accent-sky)'}
                stroke="#2b2b2b"
                strokeWidth={agent?.isCeo ? 3 : 1.5}
              />
              <text x={n.x} y={n.y + size / 2 + 12} fontSize={10} textAnchor="middle">
                {agent?.name ?? n.id}
              </text>
            </g>
          )
        })}
      </svg>
      <div style={{ marginTop: 8, fontSize: '0.8rem', color: '#666' }}>
        {Object.entries(ACT_COLOR).map(([act, color]) => (
          <span key={act} style={{ marginRight: 12 }}>
            <span style={{ display: 'inline-block', width: 10, height: 10, background: color, marginRight: 4 }} />
            {act}
          </span>
        ))}
      </div>
    </div>
  )
}
