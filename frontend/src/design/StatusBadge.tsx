import type { AgentStatus } from '../lib/types'

const STATUS_COLOR: Record<AgentStatus, string> = {
  idle: 'var(--status-idle)',
  thinking: 'var(--status-thinking)',
  working: 'var(--status-working)',
  waiting: 'var(--status-waiting)',
  blocked: 'var(--status-blocked)',
  success: 'var(--status-success)',
  ghost: 'var(--status-ghost)',
  compacting: 'var(--status-compacting)',
  looping: 'var(--status-looping)',
  typing: 'var(--status-typing)',
}

const LIVE_STATUSES: AgentStatus[] = ['thinking', 'working', 'looping', 'typing']

export function StatusBadge({ status }: { status: AgentStatus }) {
  return (
    <span className="corp-badge" style={{ background: STATUS_COLOR[status], display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <span
        className={`corp-status-dot${LIVE_STATUSES.includes(status) ? ' corp-status-dot--live' : ''}`}
        style={{ background: 'var(--corp-on-accent)' }}
      />
      {status}
    </span>
  )
}
