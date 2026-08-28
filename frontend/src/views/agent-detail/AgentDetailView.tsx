import { useEffect, useState } from 'react'
import { Icon } from '../../components/Icon'
import { PixelBadge } from '../../components/PixelBadge'
import { EditAgentModal } from '../../components/EditAgentModal'
import {
  addAgentSkill,
  approveAgentSkill,
  deleteAgentSkill,
  listAgentSkills,
  pauseAgent,
  resumeAgent,
  watchAgentSession,
  watchMessages,
  type AgentCustomSkill,
  type MessageEntry,
} from '../../lib/platformClient'
import { SKILLS_BY_DEPARTMENT } from '../../lib/skills'
import { TerminalView } from '../terminal/TerminalView'
import type { Agent } from '../../lib/types'

type DetailTab = 'terminal' | 'messages' | 'skills'

function AgentSkills({
  orgId,
  agent,
  custom,
  refresh,
}: {
  orgId: string
  agent: Agent
  custom: AgentCustomSkill[]
  refresh: () => Promise<void>
}) {
  const builtIn = SKILLS_BY_DEPARTMENT[agent.department] ?? []
  const [title, setTitle] = useState('')
  const [instructions, setInstructions] = useState('')
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try {
      await addAgentSkill(orgId, agent.id, title.trim(), instructions.trim())
      setTitle('')
      setInstructions('')
      await refresh()
    } finally {
      setSaving(false)
    }
  }

  async function remove(skillId: string) {
    await deleteAgentSkill(orgId, agent.id, skillId)
    await refresh()
  }

  async function approve(skillId: string) {
    await approveAgentSkill(orgId, agent.id, skillId)
    await refresh()
  }

  const active = custom.filter((s) => s.status !== 'pending')
  const pending = custom.filter((s) => s.status === 'pending')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="corp-panel">
        <h4 style={{ marginTop: 0 }}>Built-in</h4>
        {builtIn.length === 0 && <p className="corp-text-muted">No curated skill excerpts for this department yet — see /THIRD_PARTY_SKILLS.md.</p>}
        {builtIn.map((s) => (
          <div key={`${s.stage}-${s.skill}`} className="corp-divider-row" style={{ minWidth: 0 }}>
            <strong>{s.stage}</strong>
            <div style={{ fontSize: '0.9rem', overflowWrap: 'anywhere' }}>
              {s.author ? (
                <>
                  adapted from <em>{s.skill}</em> by {s.author}
                </>
              ) : (
                <>
                  house skill: <em>{s.skill}</em>
                </>
              )}
            </div>
            {s.source && <div className="corp-text-muted" style={{ fontSize: '0.8rem', overflowWrap: 'anywhere' }}>{s.source}</div>}
          </div>
        ))}
      </div>

      {pending.length > 0 && (
        <div className="corp-panel">
          <h4 style={{ marginTop: 0 }}>AI-suggested, pending your review</h4>
          <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
            This agent proposed these for itself after a task, based on what it learned — they don't affect its
            behavior until you approve them.
          </p>
          {pending.map((s) => (
            <div key={s.id} className="corp-divider-row" style={{ display: 'flex', justifyContent: 'space-between', gap: 8, minWidth: 0 }}>
              <div style={{ minWidth: 0 }}>
                <strong>{s.title}</strong>
                <div style={{ fontSize: '0.9rem', overflowWrap: 'anywhere' }}>{s.instructions}</div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <button className="corp-button" title="Approve" onClick={() => approve(s.id)}>
                  <Icon name="check" />
                </button>
                <button className="corp-button" title="Reject" onClick={() => remove(s.id)}>
                  <Icon name="x" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="corp-panel">
        <h4 style={{ marginTop: 0 }}>Custom, added by your org</h4>
        {active.length === 0 && <p className="corp-text-muted">No custom skills added yet.</p>}
        {active.map((s) => (
          <div key={s.id} className="corp-divider-row" style={{ display: 'flex', justifyContent: 'space-between', gap: 8, minWidth: 0 }}>
            <div style={{ minWidth: 0 }}>
              <strong>{s.title}</strong>
              <div style={{ fontSize: '0.9rem', overflowWrap: 'anywhere' }}>{s.instructions}</div>
            </div>
            <button className="corp-button" title="Delete" onClick={() => remove(s.id)} style={{ flexShrink: 0 }}>
              <Icon name="trash" />
            </button>
          </div>
        ))}

        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <input placeholder="Skill title (e.g. 'Always escalate P1s')" value={title} onChange={(e) => setTitle(e.target.value)} />
          <textarea
            rows={3}
            placeholder="Instructions this agent should follow in addition to its normal job"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
          <button className="corp-button" onClick={save} disabled={saving || !title.trim() || !instructions.trim()}>
            {saving ? 'Adding…' : 'Add skill'}
          </button>
        </div>
      </div>
    </div>
  )
}

function AgentSessionLine({ orgId, agentId }: { orgId: string; agentId: string }) {
  const [turnCount, setTurnCount] = useState<number | null>(null)
  useEffect(() => watchAgentSession(orgId, agentId, (s) => setTurnCount(s?.turnCount ?? null)), [orgId, agentId])
  if (turnCount == null) return null
  return (
    <p className="corp-text-muted" style={{ margin: 0, marginTop: -6, fontSize: '0.8rem', flexShrink: 0 }}>
      session: {turnCount} turn{turnCount === 1 ? '' : 's'} recorded
    </p>
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
  const [customSkills, setCustomSkills] = useState<AgentCustomSkill[]>([])

  async function refreshSkills() {
    setCustomSkills(await listAgentSkills(orgId, agent.id))
  }

  useEffect(() => {
    void refreshSkills()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId, agent.id])

  const pendingSkillCount = customSkills.filter((s) => s.status === 'pending').length

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
        {agent.mood && (
          <span
            className="corp-badge"
            style={{ flexShrink: 0, display: 'inline-flex', alignItems: 'center', gap: 4 }}
            title="Current mood, self-reported"
          >
            <Icon name="sparkle" style={{ width: 10, height: 10 }} />
            {agent.mood}
          </span>
        )}
        <button className="corp-button" title="Edit persona" onClick={() => setEditing(true)} style={{ flexShrink: 0 }}>
          <Icon name="edit" />
        </button>
        <button className="corp-button" style={{ marginLeft: 'auto', flexShrink: 0 }} onClick={togglePause} disabled={busy}>
          {busy ? 'Working…' : agent.paused ? 'Resume' : 'Pause'}
        </button>
      </div>
      {agent.voice && (
        <p
          className="corp-text-muted"
          style={{ margin: 0, marginTop: -6, fontSize: '0.85rem', flexShrink: 0, display: 'flex', gap: 6, alignItems: 'baseline' }}
        >
          <strong style={{ fontStyle: 'normal', flexShrink: 0 }}>Voice:</strong>
          <span style={{ fontStyle: 'italic' }}>{agent.voice}</span>
        </p>
      )}
      {agent.goal && (
        <p
          className="corp-text-muted"
          style={{ margin: 0, marginTop: -6, fontSize: '0.85rem', flexShrink: 0, display: 'flex', gap: 6, alignItems: 'baseline' }}
        >
          <strong style={{ fontStyle: 'normal', flexShrink: 0 }}>Current goal:</strong>
          <span>{agent.goal}</span>
        </p>
      )}
      <p className="corp-text-muted" style={{ margin: 0, marginTop: -6, fontSize: '0.8rem', flexShrink: 0 }}>
        running on {agent.provider} · {agent.model}
        {agent.createdAt && ` · active since ${new Date(agent.createdAt).toLocaleDateString()}`}
      </p>
      <AgentSessionLine orgId={orgId} agentId={agent.id} />

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
          {pendingSkillCount > 0 && (
            <span className="corp-badge" style={{ background: 'var(--status-blocked)', marginLeft: 6 }}>
              {pendingSkillCount}
            </span>
          )}
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        {tab === 'terminal' && <TerminalView orgId={orgId} agentId={agent.id} />}
        {tab === 'messages' && <AgentMessages orgId={orgId} agent={agent} />}
        {tab === 'skills' && <AgentSkills orgId={orgId} agent={agent} custom={customSkills} refresh={refreshSkills} />}
      </div>

      {editing && <EditAgentModal orgId={orgId} agent={agent} onClose={() => setEditing(false)} onSaved={() => {}} />}
    </div>
  )
}
