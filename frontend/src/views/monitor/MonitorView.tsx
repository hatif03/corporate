import { useState } from 'react'
import { Icon } from '../../components/Icon'
import { PixelBadge } from '../../components/PixelBadge'
import { dispatchGoal } from '../../lib/platformClient'
import type { Agent } from '../../lib/types'

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1]) // strip the data: URL prefix
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export function MonitorView({ orgId, agents }: { orgId: string; agents: Agent[] }) {
  const [goal, setGoal] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDispatch() {
    if (!goal.trim()) return
    setSending(true)
    setError(null)
    try {
      const attachment = image ? { dataB64: await fileToBase64(image), mimeType: image.type } : undefined
      await dispatchGoal(orgId, goal, attachment)
      setGoal('')
      setImage(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Dispatch — via CEO</h3>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Describe a goal… (the CEO decomposes it into department tasks)"
          rows={3}
          style={{ width: '100%', fontFamily: 'inherit', fontSize: '1rem' }}
        />
        <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button className="corp-button" onClick={handleDispatch} disabled={sending}>
            {sending ? 'Sending…' : 'Dispatch'}
          </button>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setImage(e.target.files?.[0] ?? null)}
            style={{ fontSize: '0.85rem' }}
          />
          {image && <span className="corp-text-muted" style={{ fontSize: '0.85rem' }}>{image.name}</span>}
        </div>
        {error && <p style={{ color: 'var(--corp-coral)' }}>{error}</p>}
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Agents</h3>
        {agents.length === 0 && <p className="corp-text-muted">No agents registered yet — run scripts/seed.py.</p>}
        {agents.map((a) => (
          <div key={a.id} className="corp-divider-row" style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
            <span style={{ flex: '0 0 160px', display: 'inline-flex', alignItems: 'center', gap: 4, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <strong>{a.name}</strong>
              {a.isCeo && <span aria-label="CEO"><Icon name="crown" style={{ width: 12, height: 12 }} /></span>}
            </span>
            <span className="corp-text-muted" style={{ flex: '0 0 140px', fontSize: '0.85rem' }}>{a.department}</span>
            <PixelBadge status={a.status} style={{ flexShrink: 0 }} />
            <span
              className="corp-text-muted"
              style={{ flex: 1, fontSize: '0.85rem', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={a.action || a.note || undefined}
            >
              {a.action || a.note || '—'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
