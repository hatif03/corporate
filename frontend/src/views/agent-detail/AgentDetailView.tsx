import { useEffect, useState } from 'react'
import { Crown, Mail, Terminal as TerminalIcon } from 'lucide-react'
import { StatusBadge } from '../../design/StatusBadge'
import { pauseAgent, resumeAgent, watchMessages, type MessageEntry } from '../../lib/platformClient'
import { TerminalView } from '../terminal/TerminalView'
import type { Agent } from '../../lib/types'

type DetailTab = 'terminal' | 'messages'

function AgentMessages({ orgId, agent }: { orgId: string; agent: Agent }) {
  const [messages, setMessages] = useState<MessageEntry[]>([])

  useEffect(() => watchMessages(orgId, setMessages), [orgId])

  const relevant = messages.filter((m) => m.from === agent.id || m.to === agent.id)

  return (
    <div className="corp-panel">
      {relevant.length === 0 && <p>No messages for this agent yet.</p>}
      {relevant.map((m) => (
        <div key={m.id} className="corp-divider-row" style={{ fontSize: '0.9rem' }}>
          <strong>{m.from} → {m.to}</strong>{' '}
          <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>{m.act}</span>
          <div>{m.subject}</div>
          <div className="corp-text-muted" style={{ fontSize: '0.8rem' }}>{m.createdAt}</div>
        </div>
      ))}
    </div>
  )
}

export function AgentDetailView({ orgId, agent }: { orgId: string; agent: Agent }) {
  const [tab, setTab] = useState<DetailTab>('terminal')
  const [busy, setBusy] = useState(false)

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
    <div className="corp-panel" style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', minHeight: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <h3 style={{ margin: 0 }}>
          {agent.name} {agent.isCeo && <Crown size={14} aria-label="CEO" style={{ verticalAlign: -2 }} />}
        </h3>
        <span className="corp-text-muted">{agent.department}</span>
        <StatusBadge status={agent.status} />
        <button className="corp-button" style={{ marginLeft: 'auto' }} onClick={togglePause} disabled={busy}>
          {busy ? 'Working…' : agent.paused ? 'Resume' : 'Pause'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button
          className={`corp-button${tab === 'terminal' ? ' corp-button--active' : ''}`}
          onClick={() => setTab('terminal')}
        >
          <TerminalIcon size={14} aria-hidden style={{ marginRight: 4, verticalAlign: -2 }} />
          Terminal
        </button>
        <button
          className={`corp-button${tab === 'messages' ? ' corp-button--active' : ''}`}
          onClick={() => setTab('messages')}
        >
          <Mail size={14} aria-hidden style={{ marginRight: 4, verticalAlign: -2 }} />
          Messages
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        {tab === 'terminal' && <TerminalView orgId={orgId} agentId={agent.id} />}
        {tab === 'messages' && <AgentMessages orgId={orgId} agent={agent} />}
      </div>
    </div>
  )
}
