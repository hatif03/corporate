// Directly answers a platform question raised earlier this project ("how
// does a user customize an agent") that never got a UI answer — renames,
// rewrites the bio, and picks a different sprite variant/accent color for
// an EXISTING agent. Not a "create a new department" flow: that still
// needs real code (prompts, ADK pipeline stages) via the new-department
// Claude Code skill, which no modal can fake.

import { useState } from 'react'
import { Icon } from './Icon'
import { PixelButton } from './PixelButton'
import { PixelPanel, type AccentColorName } from './PixelPanel'
import { updateAgentPersona } from '../lib/platformClient'
import type { Agent } from '../lib/types'

const ACCENTS: AccentColorName[] = ['coral', 'mint', 'sky', 'lemon', 'lilac', 'peach']
const CHARACTERS = Array.from({ length: 8 }, (_, i) => `char_${i}`)

export function EditAgentModal({ orgId, agent, onClose, onSaved }: { orgId: string; agent: Agent; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(agent.name)
  const [description, setDescription] = useState(agent.description)
  const [character, setCharacter] = useState(agent.character)
  const [accentColor, setAccentColor] = useState(agent.accentColor)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try {
      await updateAgentPersona(orgId, agent.id, { name, description, character, accent_color: accentColor })
      onSaved()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(26, 19, 32, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(420px, 92vw)' }}>
        <PixelPanel variant="dialog">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--corp-space-3)' }}>
            <h3 style={{ margin: 0, fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-sm)' }}>Edit persona</h3>
            <PixelButton variant="ghost" size="sm" onClick={onClose} title="Close">
              <Icon name="x" />
            </PixelButton>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--corp-space-3)' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span className="corp-text-muted" style={{ fontSize: 'var(--corp-text-body-sm)' }}>Name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span className="corp-text-muted" style={{ fontSize: 'var(--corp-text-body-sm)' }}>Bio</span>
              <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>

            <div>
              <span className="corp-text-muted" style={{ fontSize: 'var(--corp-text-body-sm)' }}>Accent color</span>
              <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                {ACCENTS.map((a) => (
                  <button
                    key={a}
                    title={a}
                    onClick={() => setAccentColor(a)}
                    style={{
                      width: 24,
                      height: 24,
                      background: `var(--corp-${a})`,
                      boxShadow: accentColor === a ? 'inset 0 0 0 2px var(--corp-ink-900)' : 'inset 0 0 0 1px var(--corp-ink-300)',
                      cursor: 'pointer',
                    }}
                  />
                ))}
              </div>
            </div>

            <div>
              <span className="corp-text-muted" style={{ fontSize: 'var(--corp-text-body-sm)' }}>Sprite variant</span>
              <select value={character} onChange={(e) => setCharacter(e.target.value)} style={{ display: 'block', marginTop: 4, width: '100%' }}>
                {CHARACTERS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <PixelButton variant="primary" fullWidth onClick={save} disabled={saving || !name.trim()}>
              {saving ? 'Saving…' : 'Save'}
            </PixelButton>
          </div>
        </PixelPanel>
      </div>
    </div>
  )
}
