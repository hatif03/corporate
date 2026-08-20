import { useEffect, useState } from 'react'
import { searchMemory, watchAgentMemory, type MemoryEntry, type MemoryHit } from '../../lib/platformClient'
import type { Agent } from '../../lib/types'

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
            {hits.map((h) => (
              <div key={h.memoryId} style={{ borderBottom: '1px solid #ddd', padding: '6px 0' }}>
                <strong>{h.agentId}</strong>{' '}
                <span style={{ color: '#888', fontSize: '0.8rem' }}>score {h.score.toFixed(2)}</span>
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
          {entries.map((e) => (
            <div key={e.id} style={{ borderBottom: '1px solid #ddd', padding: '6px 0', fontSize: '0.9rem' }}>
              {e.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
