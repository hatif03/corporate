import { useEffect, useState } from 'react'
import {
  createTrigger,
  deleteTrigger,
  toggleTrigger,
  watchTriggers,
} from '../../lib/platformClient'
import type { Trigger, TriggerType } from '../../lib/types'

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
        <h3 style={{ marginTop: 0 }}>Triggers</h3>
        {triggers.length === 0 && <p>No triggers configured.</p>}
        {triggers.map((t) => (
          <div key={t.id} className="corp-divider-row">
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
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
