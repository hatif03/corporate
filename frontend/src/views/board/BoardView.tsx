import { useEffect, useState } from 'react'
import { watchBoard, type BoardNote } from '../../lib/platformClient'

// orgs/{orgId}/board/main — the CEO's shared company blackboard
// (write_board tool, app/adk_agents/tools/universal.py). Previously had no
// frontend surface at all despite being a real, live-written collection.
export function BoardView({ orgId }: { orgId: string }) {
  const [note, setNote] = useState<BoardNote | null>(null)

  useEffect(() => watchBoard(orgId, setNote), [orgId])

  return (
    <div className="corp-panel">
      <h3 style={{ marginTop: 0 }}>Company board</h3>
      <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
        The CEO's shared blackboard — cross-department notes worth keeping visible.
      </p>
      {!note && <p>Nothing posted to the board yet.</p>}
      {note && (
        <>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>{note.markdown}</div>
          {note.updatedAt && (
            <div className="corp-text-muted" style={{ fontSize: '0.8rem', marginTop: 8 }}>
              last updated {new Date(note.updatedAt).toLocaleString()}
              {note.updatedBy && ` by ${note.updatedBy}`}
            </div>
          )}
        </>
      )}
    </div>
  )
}
