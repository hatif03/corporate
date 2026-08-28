import { Icon } from '../../components/Icon'
import type { Task, TaskStatus } from '../../lib/types'

const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: 'todo', label: 'Todo' },
  { status: 'doing', label: 'Doing' },
  { status: 'blocked', label: 'Blocked' },
  { status: 'done', label: 'Done' },
]

function TaskCard({ task }: { task: Task }) {
  // finance_audit/engineering_sre already return this (shared/verification.py
  // + the Gemma cross-model checker, ADR-0019) — the data existed before now,
  // this is the first time it's actually rendered anywhere.
  const verified = task.result?.verified
  return (
    <div className="corp-panel" style={{ marginBottom: 8 }}>
      <strong>{task.title}</strong>
      <div className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
        {task.assignee ?? 'unassigned'} · priority {task.priority}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
        {task.hasPendingHumanQa && (
          <span className="corp-badge" style={{ background: 'var(--status-blocked)' }}>
            needs human
          </span>
        )}
        {typeof verified === 'boolean' && (
          <span
            className="corp-badge"
            style={{ background: verified ? 'var(--corp-mint-light)' : 'var(--corp-coral)' }}
            title={verified ? 'Passed deterministic checks and an independent Gemma model review' : 'An independent Gemma model review flagged this'}
          >
            {verified ? '✓ independently verified' : '⚠ independent review flagged'}
          </span>
        )}
      </div>
      {Boolean(task.result?.videoGenerating) && !task.result?.videoUrl && (
        <div
          className="corp-divider-row"
          style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6, fontSize: '0.8rem' }}
        >
          <span className="corp-status-dot corp-status-dot--live" style={{ background: 'var(--corp-lilac)' }} />
          <Icon name="image" style={{ width: 12, height: 12 }} />
          Promo video generating (Veo) — check back shortly.
        </div>
      )}
      {typeof task.result?.videoUrl === 'string' && (
        <video controls src={task.result.videoUrl} style={{ marginTop: 6, width: '100%', borderRadius: 6 }} />
      )}
    </div>
  )
}

export function TasksView({ tasks }: { tasks: Task[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
      {COLUMNS.map((col) => {
        const columnTasks = tasks.filter((t) => t.status === col.status)
        return (
          <div key={col.status}>
            <h4>
              {col.label} <span className="corp-text-muted">{columnTasks.length}</span>
            </h4>
            {columnTasks.map((t) => (
              <TaskCard key={t.id} task={t} />
            ))}
          </div>
        )
      })}
    </div>
  )
}
