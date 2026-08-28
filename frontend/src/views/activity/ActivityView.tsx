import { useEffect, useState } from 'react'
import { getAuditStatus, toDisplayDate, watchActivity, type ActivityEntry, type AuditStatus } from '../../lib/platformClient'

const AUDIT_POLL_MS = 60_000

function AuditChainStatus({ orgId }: { orgId: string }) {
  const [status, setStatus] = useState<AuditStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function check() {
      try {
        const s = await getAuditStatus(orgId)
        if (!cancelled) {
          setStatus(s)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      }
    }
    void check()
    const id = window.setInterval(() => void check(), AUDIT_POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [orgId])

  if (error) return <p style={{ color: 'var(--corp-coral)', fontSize: '0.85rem' }}>Audit chain check failed: {error}</p>
  if (!status) return null

  return (
    <div
      className="corp-panel"
      style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem' }}
    >
      <span
        className="corp-status-dot corp-status-dot--live"
        style={{ background: status.ok ? 'var(--corp-mint)' : 'var(--corp-coral)' }}
      />
      {status.ok
        ? `Tamper-evident audit chain intact — ${status.entry_count} entries`
        : `Audit chain broken at entry ${status.broken_at ?? '?'}: ${status.reason ?? 'unknown reason'}`}
    </div>
  )
}

export function ActivityView({ orgId }: { orgId: string }) {
  const [entries, setEntries] = useState<ActivityEntry[]>([])

  useEffect(() => watchActivity(orgId, setEntries), [orgId])

  return (
    <div className="corp-panel">
      <AuditChainStatus orgId={orgId} />
      {entries.length === 0 && <p>No activity yet.</p>}
      {entries.map((e) => {
        const when = toDisplayDate(e.ts)
        return (
          <div key={e.id} className="corp-divider-row" style={{ fontSize: '0.9rem' }}>
            <span className="corp-text-muted">{e.type}</span> — <strong>{e.agentId}</strong>: {e.message}
            {when && <div className="corp-text-muted" style={{ fontSize: '0.8rem' }}>{when.toLocaleString()}</div>}
          </div>
        )
      })}
    </div>
  )
}
