import type { Task, TaskStatus } from '../../lib/types'

const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: 'todo', label: 'Todo' },
  { status: 'doing', label: 'Doing' },
  { status: 'blocked', label: 'Blocked' },
  { status: 'done', label: 'Done' },
]

function TaskCard({ task }: { task: Task }) {
  return (
    <div className="corp-panel" style={{ marginBottom: 8 }}>
      <strong>{task.title}</strong>
      <div className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
        {task.assignee ?? 'unassigned'} · priority {task.priority}
      </div>
      {task.hasPendingHumanQa && (
        <div style={{ marginTop: 4 }}>
          <span className="corp-badge" style={{ background: 'var(--status-blocked)' }}>
            needs human
          </span>
        </div>
      )}
      {Boolean(task.result?.videoGenerating) && !task.result?.videoUrl && (
        <p className="corp-text-muted" style={{ fontSize: '0.8rem', marginTop: 4, marginBottom: 0 }}>
          Promo video generating (Veo) — check back shortly.
        </p>
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
