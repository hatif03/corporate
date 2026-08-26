import { useEffect, useState } from 'react'
import { Icon } from '../../components/Icon'
import { PixelBadge } from '../../components/PixelBadge'
import { EditAgentModal } from '../../components/EditAgentModal'
import { pauseAgent, resumeAgent, watchMessages, type MessageEntry } from '../../lib/platformClient'
import { SKILLS_BY_DEPARTMENT } from '../../lib/skills'
import { TerminalView } from '../terminal/TerminalView'
import type { Agent } from '../../lib/types'

type DetailTab = 'terminal' | 'messages' | 'skills'

function AgentSkills({ agent }: { agent: Agent }) {
  const skills = SKILLS_BY_DEPARTMENT[agent.department] ?? []
  return (
    <div className="corp-panel">
      {skills.length === 0 && <p className="corp-text-muted">No curated skill excerpts for this department yet — see /THIRD_PARTY_SKILLS.md.</p>}
      {skills.map((s) => (
        <div key={`${s.stage}-${s.skill}`} className="corp-divider-row" style={{ minWidth: 0 }}>
          <strong>{s.stage}</strong>
          <div style={{ fontSize: '0.9rem', overflowWrap: 'anywhere' }}>
            adapted from <em>{s.skill}</em> by {s.author}
          </div>
          <div className="corp-text-muted" style={{ fontSize: '0.8rem', overflowWrap: 'anywhere' }}>{s.source}</div>
        </div>
      ))}
    </div>
  )
}

function AgentMessages({ orgId, agent }: { orgId: string; agent: Agent }) {
  const [messages, setMessages] = useState<MessageEntry[]>([])

  useEffect(() => watchMessages(orgId, setMessages), [orgId])

  const relevant = messages.filter((m) => m.from === agent.id || m.to === agent.id)

  return (
    <div className="corp-panel">
      {relevant.length === 0 && <p>No messages for this agent yet.</p>}
      {relevant.map((m) => (
        <div key={m.id} className="corp-divider-row" style={{ fontSize: '0.9rem', minWidth: 0 }}>
          <strong>{m.from} → {m.to}</strong>{' '}
          <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>{m.act}</span>
          <div style={{ overflowWrap: 'anywhere' }}>{m.subject}</div>
          <div className="corp-text-muted" style={{ fontSize: '0.8rem' }}>{m.createdAt}</div>
        </div>
      ))}
    </div>
  )
}

export function AgentDetailView({ orgId, agent }: { orgId: string; agent: Agent }) {
  const [tab, setTab] = useState<DetailTab>('terminal')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)

  async function togglePause() {
    setBusy(true)
    try {
      if (agent.paused) await resumeAgent(orgId, agent.id)
      else await pauseAgent(orgId, agent.id)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="corp-panel" style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', minHeight: 0, minWidth: 0, overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0, minWidth: 0, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {agent.name} {agent.isCeo && <span aria-label="CEO"><Icon name="crown" style={{ verticalAlign: -2 }} /></span>}
        </h3>
        <span className="corp-text-muted" style={{ flexShrink: 0 }}>{agent.department}</span>
        <PixelBadge status={agent.status} style={{ flexShrink: 0 }} />
        <button className="corp-button" title="Edit persona" onClick={() => setEditing(true)} style={{ flexShrink: 0 }}>
          <Icon name="edit" />
        </button>
        <button className="corp-button" style={{ marginLeft: 'auto', flexShrink: 0 }} onClick={togglePause} disabled={busy}>
          {busy ? 'Working…' : agent.paused ? 'Resume' : 'Pause'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button
          className={`corp-button${tab === 'terminal' ? ' corp-button--active' : ''}`}
          onClick={() => setTab('terminal')}
        >
          <Icon name="terminal" style={{ marginRight: 4, verticalAlign: -2 }} />
          Terminal
        </button>
        <button
          className={`corp-button${tab === 'messages' ? ' corp-button--active' : ''}`}
          onClick={() => setTab('messages')}
        >
          <Icon name="mail" style={{ marginRight: 4, verticalAlign: -2 }} />
          Messages
        </button>
        <button
          className={`corp-button${tab === 'skills' ? ' corp-button--active' : ''}`}
          onClick={() => setTab('skills')}
        >
          <Icon name="sparkle" style={{ marginRight: 4, verticalAlign: -2 }} />
          Skills
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        {tab === 'terminal' && <TerminalView orgId={orgId} agentId={agent.id} />}
        {tab === 'messages' && <AgentMessages orgId={orgId} agent={agent} />}
        {tab === 'skills' && <AgentSkills agent={agent} />}
      </div>

      {editing && <EditAgentModal orgId={orgId} agent={agent} onClose={() => setEditing(false)} onSaved={() => {}} />}
    </div>
  )
}
