import { useEffect, useState } from 'react'
import { toDisplayDate, watchActivity, type ActivityEntry } from '../../lib/platformClient'

export function ActivityView({ orgId }: { orgId: string }) {
  const [entries, setEntries] = useState<ActivityEntry[]>([])

  useEffect(() => watchActivity(orgId, setEntries), [orgId])

  return (
    <div className="corp-panel">
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
