import { useEffect, useState } from 'react'
import { watchActivity, type ActivityEntry } from '../../lib/platformClient'

export function ActivityView({ orgId }: { orgId: string }) {
  const [entries, setEntries] = useState<ActivityEntry[]>([])

  useEffect(() => watchActivity(orgId, setEntries), [orgId])

  return (
    <div className="corp-panel">
      {entries.length === 0 && <p>No activity yet.</p>}
      {entries.map((e) => (
        <div key={e.id} className="corp-divider-row" style={{ fontSize: '0.9rem' }}>
          <span className="corp-text-muted">{e.type}</span> — <strong>{e.agentId}</strong>: {e.message}
        </div>
      ))}
    </div>
  )
}
