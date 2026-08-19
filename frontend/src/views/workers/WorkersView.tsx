import { useEffect, useState } from 'react'
import { spawnWorker, stopWorker, watchWorkers } from '../../lib/platformClient'
import type { Worker } from '../../lib/types'

const STATUS_COLOR: Record<Worker['status'], string> = {
  spawned: 'var(--status-idle)',
  running: 'var(--status-working)',
  done: 'var(--status-success)',
  failed: 'var(--status-blocked)',
}

export function WorkersView({ orgId }: { orgId: string }) {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [prompt, setPrompt] = useState('')

  useEffect(() => watchWorkers(orgId, setWorkers), [orgId])

  async function submit() {
    if (!prompt.trim()) return
    await spawnWorker(orgId, 'manual-test', prompt)
    setPrompt('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Spawn a test worker</h3>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="An inbound event to hand to an ephemeral worker…"
          rows={2}
          style={{ width: '100%', fontFamily: 'inherit' }}
        />
        <div style={{ marginTop: 8 }}>
          <button className="corp-button" onClick={submit}>
            Spawn
          </button>
        </div>
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Workers</h3>
        {workers.length === 0 && <p>No workers running right now.</p>}
        {workers.map((w) => (
          <div key={w.id} style={{ borderBottom: '1px solid #ddd', padding: '8px 0' }}>
            <strong>{w.id}</strong>{' '}
            <span className="corp-badge" style={{ background: STATUS_COLOR[w.status] }}>
              {w.status}
            </span>
            <div style={{ fontSize: '0.85rem', color: '#555' }}>from: {w.sourceEvent}</div>
            {w.result?.reply != null && <div style={{ fontSize: '0.85rem' }}>{String(w.result.reply)}</div>}
            {w.result?.error != null && (
              <div style={{ fontSize: '0.85rem', color: 'var(--corp-accent-coral)' }}>{String(w.result.error)}</div>
            )}
            {w.status === 'running' && (
              <button className="corp-button" style={{ marginTop: 4 }} onClick={() => stopWorker(orgId, w.id)}>
                Stop
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
