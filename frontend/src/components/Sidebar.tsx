import { DEPARTMENT_ZONES } from '../scene/office/departments'
import { AgentRosterItem } from './AgentRosterItem'
import type { CSSProperties } from 'react'
import type { Agent } from '../lib/types'

const SECTION_HEADER_STYLE: CSSProperties = {
  margin: '0 0 6px',
  fontFamily: 'var(--corp-font-display)',
  fontSize: 'var(--corp-text-display-sm)',
  lineHeight: 'var(--corp-lh-display-sm)',
  textTransform: 'uppercase',
  color: 'var(--corp-ink-500)',
  letterSpacing: '0.03em',
}

export function Sidebar({
  agents,
  selectedAgentId,
  onSelect,
}: {
  agents: Agent[]
  selectedAgentId: string | null
  onSelect: (agentId: string) => void
}) {
  const ceoAgents = agents.filter((a) => a.isCeo)
  const rankAndFile = agents.filter((a) => !a.isCeo)

  return (
    <div
      className="corp-panel"
      style={{ width: 'var(--corp-sidebar-width)', flexShrink: 0, height: '100%', minHeight: 0, overflowY: 'auto' }}
    >
      {ceoAgents.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={SECTION_HEADER_STYLE}>Office of the CEO</h4>
          {ceoAgents.map((a) => (
            <AgentRosterItem key={a.id} agent={a} selected={a.id === selectedAgentId} onSelect={onSelect} />
          ))}
        </div>
      )}
      {DEPARTMENT_ZONES.map((zone) => {
        const zoneAgents = rankAndFile.filter((a) => a.department === zone.id)
        if (zoneAgents.length === 0) return null
        return (
          <div key={zone.id} style={{ marginBottom: 16 }}>
            <h4 style={SECTION_HEADER_STYLE}>{zone.displayName}</h4>
            {zoneAgents.map((a) => (
              <AgentRosterItem key={a.id} agent={a} selected={a.id === selectedAgentId} onSelect={onSelect} />
            ))}
          </div>
        )
      })}
    </div>
  )
}
