import { useState } from 'react'
import { StatusBadge } from '../../design/StatusBadge'
import { dispatchGoal } from '../../lib/platformClient'
import type { Agent } from '../../lib/types'

export function MonitorView({ orgId, agents }: { orgId: string; agents: Agent[] }) {
  const [goal, setGoal] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDispatch() {
    if (!goal.trim()) return
    setSending(true)
    setError(null)
    try {
      await dispatchGoal(orgId, goal)
      setGoal('')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Dispatch — via CEO</h3>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Describe a goal… (the CEO decomposes it into department tasks)"
          rows={3}
          style={{ width: '100%', fontFamily: 'inherit', fontSize: '1rem' }}
        />
        <div style={{ marginTop: 8 }}>
          <button className="corp-button" onClick={handleDispatch} disabled={sending}>
            {sending ? 'Sending…' : 'Dispatch'}
          </button>
        </div>
        {error && <p style={{ color: 'var(--corp-accent-coral)' }}>{error}</p>}
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Agents</h3>
        {agents.length === 0 && <p>No agents registered yet — run scripts/seed.py.</p>}
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              <th>Name</th>
              <th>Department</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.id}>
                <td>
                  {a.name} {a.isCeo && <span title="CEO">👑</span>}
                </td>
                <td>{a.department}</td>
                <td>
                  <StatusBadge status={a.status} />
                </td>
                <td>{a.action || a.note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
