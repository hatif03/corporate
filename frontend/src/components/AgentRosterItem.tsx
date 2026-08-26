import { StatusBadge } from '../design/StatusBadge'
import type { Agent } from '../lib/types'

export function AgentRosterItem({
  agent,
  selected,
  onSelect,
}: {
  agent: Agent
  selected: boolean
  onSelect: (agentId: string) => void
}) {
  return (
    <button
      className="corp-button"
      onClick={() => onSelect(agent.id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        width: '100%',
        marginBottom: 4,
        background: selected ? 'var(--corp-accent-sky)' : undefined,
      }}
    >
      <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {agent.name} {agent.isCeo && <span title="CEO">👑</span>}
      </span>
      <StatusBadge status={agent.status} />
    </button>
  )
}
