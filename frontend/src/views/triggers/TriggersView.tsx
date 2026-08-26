import { useEffect, useState } from 'react'
import { Collapsible } from '../../components/Collapsible'
import {
  createTrigger,
  deleteTrigger,
  getTriggerHistory,
  toggleTrigger,
  watchTriggers,
  type TriggerHistoryEntry,
} from '../../lib/platformClient'
import type { Trigger, TriggerType } from '../../lib/types'

function TriggerHistoryList({ orgId, triggerId }: { orgId: string; triggerId: string }) {
  const [history, setHistory] = useState<TriggerHistoryEntry[] | null>(null)

  useEffect(() => {
    getTriggerHistory(orgId, triggerId).then(setHistory)
  }, [orgId, triggerId])

  if (history === null) return <p className="corp-text-muted" style={{ fontSize: '0.8rem' }}>Loading…</p>
  if (history.length === 0) return <p className="corp-text-muted" style={{ fontSize: '0.8rem' }}>Never fired yet.</p>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {history.map((h) => (
        <div key={h.id} className="corp-text-muted" style={{ fontSize: '0.8rem' }}>
          {new Date(h.firedAt).toLocaleString()} — {h.payloadPreview || '(empty payload)'}
        </div>
      ))}
    </div>
  )
}

function TriggerRow({ orgId, t }: { orgId: string; t: Trigger }) {
  const [showHistory, setShowHistory] = useState(false)
  return (
    <div className="corp-divider-row">
      <strong>{t.name}</strong> <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>{t.type}</span>
      <div className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
        → {t.targetAgent} {t.cron && `· ${t.cron}`}
        {t.lastFiredAt && ` · last fired ${new Date(t.lastFiredAt).toLocaleString()}`}
      </div>
      {t.type === 'webhook' && t.webhookSecret && (
        <div className="corp-text-muted" style={{ fontSize: '0.75rem' }}>secret: {t.webhookSecret}</div>
      )}
      <div style={{ marginTop: 4, display: 'flex', gap: 8 }}>
        <button className="corp-button" onClick={() => toggleTrigger(orgId, t.id, !t.enabled)}>
          {t.enabled ? 'Disable' : 'Enable'}
        </button>
        <button className="corp-button" onClick={() => deleteTrigger(orgId, t.id)}>
          Delete
        </button>
        <button className="corp-button" onClick={() => setShowHistory((s) => !s)}>
          {showHistory ? 'Hide history' : 'History'}
        </button>
      </div>
      {showHistory && (
        <div style={{ marginTop: 6 }}>
          <TriggerHistoryList orgId={orgId} triggerId={t.id} />
        </div>
      )}
    </div>
  )
}

export function TriggersView({ orgId }: { orgId: string }) {
  const [triggers, setTriggers] = useState<Trigger[]>([])
  const [name, setName] = useState('')
  const [type, setType] = useState<TriggerType>('webhook')
  const [targetAgent, setTargetAgent] = useState('engineering_sre')
  const [payloadTemplate, setPayloadTemplate] = useState('{payload}')
  const [cron, setCron] = useState('0 * * * *')

  useEffect(() => watchTriggers(orgId, setTriggers), [orgId])

  async function submit() {
    if (!name.trim()) return
    await createTrigger(orgId, {
      name,
      type,
      target_agent: targetAgent,
      payload_template: payloadTemplate,
      cron: type === 'schedule' ? cron : undefined,
    })
    setName('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Add a trigger</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <select value={type} onChange={(e) => setType(e.target.value as TriggerType)}>
            <option value="webhook">Webhook</option>
            <option value="schedule">Schedule</option>
          </select>
          <input
            placeholder="Target agent id (e.g. engineering_sre)"
            value={targetAgent}
            onChange={(e) => setTargetAgent(e.target.value)}
          />
          {type === 'schedule' && (
            <input placeholder="Cron expression" value={cron} onChange={(e) => setCron(e.target.value)} />
          )}
          <input
            placeholder="Payload template ({payload} is replaced with the raw event)"
            value={payloadTemplate}
            onChange={(e) => setPayloadTemplate(e.target.value)}
            style={{ gridColumn: '1 / -1' }}
          />
        </div>
        <div style={{ marginTop: 8 }}>
          <button className="corp-button" onClick={submit}>
            Add
          </button>
        </div>
      </div>

      <div className="corp-panel">
        <Collapsible title="Schedules" defaultOpen>
          {triggers.filter((t) => t.type === 'schedule').length === 0 && <p>No schedules configured.</p>}
          {triggers.filter((t) => t.type === 'schedule').map((t) => (
            <TriggerRow key={t.id} orgId={orgId} t={t} />
          ))}
        </Collapsible>
        <Collapsible title="Webhooks" defaultOpen>
          {triggers.filter((t) => t.type === 'webhook').length === 0 && <p>No webhooks configured.</p>}
          {triggers.filter((t) => t.type === 'webhook').map((t) => (
            <TriggerRow key={t.id} orgId={orgId} t={t} />
          ))}
        </Collapsible>
      </div>
    </div>
  )
}
