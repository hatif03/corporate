// A toast when a task transitions to done/blocked, using the task stream
// App.tsx already subscribes to (watchTasks) — no new data source. Scoped
// to any task reaching a terminal state, not "tasks the current browser
// tab dispatched": Corporate's Task model has no field tying a task back to
// the browser session that created it (createdBy is the dispatching
// agent id, e.g. "ceo"), so that finer scoping isn't backed by real data.

import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'
import type { Task } from '../lib/types'

interface ToastEntry {
  id: string
  title: string
  status: 'done' | 'blocked'
}

const VISIBLE_MS = 6000

export function CompletionToast({ tasks }: { tasks: Task[] }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const prevStatusRef = useRef<Map<string, string>>(new Map())
  const seenRef = useRef(false)

  useEffect(() => {
    const prev = prevStatusRef.current
    // First tick just establishes the baseline — don't toast for every task
    // that was already done/blocked before this component ever mounted.
    if (seenRef.current) {
      for (const t of tasks) {
        const before = prev.get(t.id)
        if (before !== t.status && (t.status === 'done' || t.status === 'blocked')) {
          const entry: ToastEntry = { id: `${t.id}-${t.status}-${Date.now()}`, title: t.title, status: t.status }
          setToasts((cur) => [...cur, entry])
          setTimeout(() => setToasts((cur) => cur.filter((x) => x.id !== entry.id)), VISIBLE_MS)
        }
      }
    }
    seenRef.current = true
    prevStatusRef.current = new Map(tasks.map((t) => [t.id, t.status]))
  }, [tasks])

  if (toasts.length === 0) return null

  return (
    <div style={{ position: 'fixed', bottom: 128, right: 16, display: 'flex', flexDirection: 'column', gap: 8, zIndex: 300 }}>
      {toasts.map((t) => (
        <div
          key={t.id}
          className="corp-panel"
          style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 240, maxWidth: 360 }}
        >
          <Icon name={t.status === 'done' ? 'check' : 'bell'} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 'var(--corp-text-body-sm)', fontWeight: 600 }}>{t.status === 'done' ? 'Task done' : 'Needs a human'}</div>
            <div className="corp-text-muted" style={{ fontSize: 'var(--corp-text-body-sm)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {t.title}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
