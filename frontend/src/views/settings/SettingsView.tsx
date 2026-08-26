import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../../lib/platformClient'

export function SettingsView({ orgId }: { orgId: string }) {
  const [limitInput, setLimitInput] = useState('')
  const [saved, setSaved] = useState<number | null | undefined>(undefined) // undefined = still loading

  useEffect(() => {
    getSettings(orgId).then((s) => {
      setSaved(s.dailyGeminiCallLimit)
      setLimitInput(s.dailyGeminiCallLimit?.toString() ?? '')
    })
  }, [orgId])

  async function submit() {
    const value = limitInput.trim() === '' ? null : Number(limitInput)
    const result = await updateSettings(orgId, value)
    setSaved(result.dailyGeminiCallLimit)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Gemini daily call budget</h3>
        <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
          Leave blank for no org-specific cap (the platform falls back to its own high emergency-brake
          ceiling — plenty for normal use, just enough to stop a genuine runaway loop). Set a low number here
          (e.g. 2) to test that the circuit breaker actually trips.
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            placeholder="e.g. 500, or blank for unlimited"
            value={limitInput}
            onChange={(e) => setLimitInput(e.target.value)}
            style={{ width: 220 }}
          />
          <button className="corp-button" onClick={submit}>
            Save
          </button>
        </div>
        {saved !== undefined && (
          <p style={{ marginTop: 8, fontSize: '0.85rem' }}>
            Current: {saved === null ? 'using the platform fallback' : `${saved} calls/day`}
          </p>
        )}
      </div>
    </div>
  )
}
