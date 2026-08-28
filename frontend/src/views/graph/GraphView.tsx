import { useEffect, useMemo, useState } from 'react'
import { watchMessages, type MessageEntry } from '../../lib/platformClient'
import { layoutGraph, HEIGHT, WIDTH, type GraphEdge, type GraphNode } from './forceLayout'
import type { Agent } from '../../lib/types'

const ACT_COLOR: Record<string, string> = {
  request: 'var(--corp-sky)',
  query: 'var(--corp-lilac)',
  propose: 'var(--corp-peach)',
  agree: 'var(--corp-mint)',
  done: 'var(--corp-mint)',
  refuse: 'var(--corp-coral)',
  inform: 'var(--corp-lemon)',
}

interface AggregatedEdge extends GraphEdge {
  lastAct: string
}

export function GraphView({
  agents,
  orgId,
  onSelectAgent,
}: {
  agents: Agent[]
  orgId: string
  onSelectAgent?: (agentId: string) => void
}) {
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

  if (messages.length === 0) {
    return (
      <div className="corp-panel">
        <p className="corp-text-muted">No inter-agent messages yet — this fills in as the CEO and departments talk to each other.</p>
      </div>
    )
  }

  return (
    <div className="corp-panel">
      <div style={{ background: 'var(--corp-paper-200)', boxShadow: 'var(--corp-border-panel-inset)' }}>
        <svg width={WIDTH} height={HEIGHT}>
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
                style={{ stroke: ACT_COLOR[act] ?? 'var(--corp-ink-300)' }}
                strokeWidth={Math.min(1 + edge.weight, 6)}
                opacity={0.7}
              />
            )
          })}
          {positioned.map((n) => {
            const agent = agents.find((a) => a.id === n.id)
            const size = 10 + Math.min(n.degree * 2, 20)
            return (
              <g
                key={n.id}
                onClick={() => agent && onSelectAgent?.(agent.id)}
                style={{ cursor: agent && onSelectAgent ? 'pointer' : 'default' }}
              >
                <rect
                  x={n.x - size / 2}
                  y={n.y - size / 2}
                  width={size}
                  height={size}
                  style={{ fill: agent?.isCeo ? 'var(--corp-lemon)' : 'var(--corp-sky)', stroke: 'var(--corp-ink-900)' }}
                  strokeWidth={agent?.isCeo ? 3 : 1.5}
                />
                <text x={n.x} y={n.y + size / 2 + 12} fontSize={10} textAnchor="middle">
                  {agent?.name ?? n.id}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      <div className="corp-text-muted" style={{ marginTop: 4, fontSize: '0.8rem' }}>
        Node size = how many messages it's sent/received · yellow = CEO · click a node to open that agent.
      </div>
      <div className="corp-text-muted" style={{ marginTop: 8, fontSize: '0.8rem' }}>
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
