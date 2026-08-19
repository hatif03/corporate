import { useEffect, useState } from 'react'
import { watchActivity, type ActivityEntry } from '../../lib/platformClient'

export function ActivityView({ orgId }: { orgId: string }) {
  const [entries, setEntries] = useState<ActivityEntry[]>([])

  useEffect(() => watchActivity(orgId, setEntries), [orgId])

  return (
    <div className="corp-panel">
      {entries.length === 0 && <p>No activity yet.</p>}
      {entries.map((e) => (
        <div key={e.id} style={{ borderBottom: '1px solid #ddd', padding: '4px 0', fontSize: '0.9rem' }}>
          <span style={{ color: '#888' }}>{e.type}</span> — <strong>{e.agentId}</strong>: {e.message}
        </div>
      ))}
    </div>
  )
}
