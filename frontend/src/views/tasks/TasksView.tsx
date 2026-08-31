import { Collapsible } from '../../components/Collapsible'
import { Icon } from '../../components/Icon'
import { toDisplayDate } from '../../lib/platformClient'
import type { Task, TaskStatus } from '../../lib/types'

interface AspectVote {
  aspect: string
  passed: boolean
  reason: string
}

const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: 'todo', label: 'Todo' },
  { status: 'doing', label: 'Doing' },
  { status: 'blocked', label: 'Blocked' },
  { status: 'done', label: 'Done' },
]

function TaskCard({ task }: { task: Task }) {
  // finance_audit/engineering_sre already return this (shared/verification.py
  // + the independent-review checker, ADR-0019) — the data existed before
  // now, this is the first time it's actually rendered anywhere.
  const verified = task.result?.verified
  const votes = task.result?.votes as AspectVote[] | undefined
  const retried = task.result?.retried
  return (
    <div className="corp-panel" style={{ marginBottom: 8 }}>
      <strong>{task.title}</strong>{' '}
      <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>{task.taskType}</span>{' '}
      <span className="corp-badge" title="Which Gemini tier this task runs on (ADR-0013)">{task.modelTier}</span>
      <div className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
        {task.assignee ?? 'unassigned'} · priority {task.priority}
        {toDisplayDate(task.createdAt) && ` · created ${toDisplayDate(task.createdAt)!.toLocaleString()}`}
      </div>
      {task.description && (
        <p style={{ fontSize: '0.85rem', margin: '4px 0 0' }}>{task.description}</p>
      )}
      {task.attachment && (
        <div className="corp-text-muted" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4 }}>
          <Icon name="image" style={{ width: 12, height: 12 }} /> attachment: {task.attachment.mimeType}
        </div>
      )}
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
            title={verified ? 'Passed deterministic checks and an independent model review' : 'An independent model review flagged this'}
          >
            {verified ? '✓ independently verified' : '⚠ independent review flagged'}
            {retried ? ' (retried)' : ''}
          </span>
        )}
      </div>
      {votes && votes.length > 0 && (
        <Collapsible title={<span style={{ fontSize: '0.8rem' }}>{votes.length} checker vote(s)</span>}>
          {votes.map((v, i) => (
            <div key={i} className="corp-text-muted" style={{ fontSize: '0.8rem', marginBottom: 2 }}>
              {v.passed ? '✓' : '✗'} <strong>{v.aspect}</strong>{v.reason ? ` — ${v.reason}` : ''}
            </div>
          ))}
        </Collapsible>
      )}
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
