import type { AgentStatus } from '../lib/types'

const STATUS_COLOR: Record<AgentStatus, string> = {
  idle: 'var(--status-idle)',
  thinking: 'var(--status-thinking)',
  working: 'var(--status-working)',
  waiting: 'var(--status-waiting)',
  blocked: 'var(--status-blocked)',
  success: 'var(--status-success)',
  ghost: 'var(--status-ghost)',
  compacting: 'var(--corp-accent-lilac)',
  looping: 'var(--corp-accent-peach)',
  typing: 'var(--status-working)',
}

export function StatusBadge({ status }: { status: AgentStatus }) {
  return (
    <span className="corp-badge" style={{ background: STATUS_COLOR[status] }}>
      {status}
    </span>
  )
}
