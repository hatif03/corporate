import { useEffect, useMemo, useState } from 'react'
import { searchMemory, toDisplayDate, watchAgentMemory, type MemoryEntry, type MemoryHit } from '../../lib/platformClient'
import { layoutGraph, HEIGHT, WIDTH } from '../graph/forceLayout'
import type { Agent } from '../../lib/types'

// A force-directed view of one search's real results — the query as a
// center node, each hit as a node connected to it, sized/colored by its
// real similarity score. No invented relatedness between memories: we
// only have per-query top-k scores, so a star graph off the query is what
// the data actually supports.
function MemoryHitGraph({ query, hits }: { query: string; hits: MemoryHit[] }) {
  const { nodes, edges } = useMemo(() => {
    const graphNodes = [{ id: 'query', degree: hits.length }, ...hits.map((h) => ({ id: h.memoryId, degree: 1 }))]
    const graphEdges = hits.map((h) => ({ source: 'query', target: h.memoryId, weight: h.score }))
    return { nodes: graphNodes, edges: graphEdges }
  }, [hits])
  const positioned = useMemo(() => layoutGraph(nodes, edges), [nodes, edges])
  const byId = new Map(hits.map((h) => [h.memoryId, h]))

  return (
    <svg width={WIDTH} height={HEIGHT} style={{ background: 'var(--corp-paper-200)', boxShadow: 'var(--corp-border-panel-inset)' }}>
      {positioned
        .filter((n) => n.id !== 'query')
        .map((n) => {
          const center = positioned.find((p) => p.id === 'query')
          if (!center) return null
          return <line key={n.id} x1={center.x} y1={center.y} x2={n.x} y2={n.y} stroke="var(--corp-ink-300)" strokeWidth={1 + (byId.get(n.id)?.score ?? 0) * 3} opacity={0.6} />
        })}
      {positioned.map((n) => {
        const hit = byId.get(n.id)
        const isCenter = n.id === 'query'
        const size = isCenter ? 16 : 8 + (hit?.score ?? 0) * 14
        return (
          <g key={n.id}>
            <rect
              x={n.x - size / 2}
              y={n.y - size / 2}
              width={size}
              height={size}
              style={{ fill: isCenter ? 'var(--corp-lemon)' : 'var(--corp-sky)', stroke: 'var(--corp-ink-900)' }}
              strokeWidth={isCenter ? 2 : 1}
            />
            <text x={n.x} y={n.y + size / 2 + 12} fontSize={9} textAnchor="middle">
              {isCenter ? query.slice(0, 16) : hit?.agentId}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export function MemoryView({ orgId, agents }: { orgId: string; agents: Agent[] }) {
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<MemoryHit[] | null>(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (agents.length > 0 && !selectedAgent) setSelectedAgent(agents[0].id)
  }, [agents, selectedAgent])

  useEffect(() => {
    if (!selectedAgent) return
    return watchAgentMemory(orgId, selectedAgent, setEntries)
  }, [orgId, selectedAgent])

  async function runSearch() {
    if (!query.trim()) return
    setSearching(true)
    try {
      setHits(await searchMemory(orgId, query))
    } finally {
      setSearching(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Semantic search — what does the hive know about…</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            style={{ flex: 1 }}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. fraud signals, auth outages, pricing discounts…"
          />
          <button className="corp-button" onClick={runSearch} disabled={searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </div>
        {hits && (
          <div style={{ marginTop: 8 }}>
            {hits.length === 0 && <p>No results.</p>}
            {hits.length > 0 && <MemoryHitGraph query={query} hits={hits} />}
            {hits.map((h) => (
              <div key={h.memoryId} className="corp-divider-row">
                <strong>{h.agentId}</strong>{' '}
                <span className="corp-text-muted" style={{ fontSize: '0.8rem' }}>score {h.score.toFixed(2)}</span>
                <div style={{ fontSize: '0.9rem' }}>{h.text}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Memory file</h3>
        <select value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)}>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <div style={{ marginTop: 8 }}>
          {entries.length === 0 && <p>No memory entries yet.</p>}
          {entries.map((e) => {
            const when = toDisplayDate(e.createdAt)
            return (
              <div key={e.id} className="corp-divider-row" style={{ fontSize: '0.9rem' }}>
                <span className="corp-badge" style={{ marginRight: 6, fontSize: '0.7rem' }}>{e.kind}</span>
                {e.text}
                {when && <div className="corp-text-muted" style={{ fontSize: '0.8rem' }}>{when.toLocaleString()}</div>}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
