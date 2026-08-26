// Adapted from the MIT-licensed reference design system's AgentStrip, see
// /THIRD_PARTY_SKILLS.md — the bottom-pinned horizontal roster (dimensions,
// padding, background) is ported as-is; drag-to-reorder and the
// note/restore-team affordances (no backing data on our side) are not.
// Replaces the earlier left-hand Sidebar/AgentRosterItem.

import { AgentCard } from './AgentCard'
import type { Agent, Task } from '../lib/types'

export function AgentStrip({
  agents,
  tasks,
  selectedAgentId,
  onSelect,
}: {
  agents: Agent[]
  tasks: Task[]
  selectedAgentId: string | null
  onSelect: (agentId: string) => void
}) {
  const doingCountByDepartment = new Map<string, number>()
  for (const t of tasks) {
    if (t.status !== 'doing' || !t.assignee) continue
    doingCountByDepartment.set(t.assignee, (doingCountByDepartment.get(t.assignee) ?? 0) + 1)
  }

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        padding: '14px 16px',
        overflowX: 'auto',
        overflowY: 'hidden',
        borderTop: '1px solid var(--corp-ink-300)',
        background: 'var(--corp-cream-200)',
        // Tall enough for the CEO card to stand proud of the row (taller,
        // rides a drop shadow) plus the hover-lift on every card.
        height: 112,
        minHeight: 112,
        flexShrink: 0,
        alignItems: 'center',
      }}
    >
      {agents.map((a) => (
        <AgentCard
          key={a.id}
          agent={a}
          selected={a.id === selectedAgentId}
          doingCount={a.isCeo ? 0 : (doingCountByDepartment.get(a.department) ?? 0)}
          onClick={() => onSelect(a.id)}
        />
      ))}
    </div>
  )
}
