import { useEffect, useState } from 'react'
import { spawnWorker, stopWorker, watchWorkers } from '../../lib/platformClient'
import type { Agent, Worker } from '../../lib/types'

const STATUS_COLOR: Record<Worker['status'], string> = {
  spawned: 'var(--status-idle)',
  running: 'var(--status-working)',
  done: 'var(--status-success)',
  failed: 'var(--status-blocked)',
}

type Step = 'briefing' | 'target'

export function WorkersView({ orgId, agents }: { orgId: string; agents: Agent[] }) {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [step, setStep] = useState<Step>('briefing')
  const [prompt, setPrompt] = useState('')
  const [targetAgent, setTargetAgent] = useState('')
  const [modelTier, setModelTier] = useState<'flash' | 'pro'>('flash')

  useEffect(() => watchWorkers(orgId, setWorkers), [orgId])

  async function submit() {
    if (!prompt.trim()) return
    await spawnWorker(orgId, 'manual-test', prompt, targetAgent || null, modelTier)
    setPrompt('')
    setTargetAgent('')
    setModelTier('flash')
    setStep('briefing')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Spawn a test worker</h3>

        {step === 'briefing' && (
          <>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="An inbound event to hand to an ephemeral worker…"
              rows={2}
              style={{ width: '100%', fontFamily: 'inherit' }}
            />
            <div style={{ marginTop: 8 }}>
              <button className="corp-button" onClick={() => prompt.trim() && setStep('target')} disabled={!prompt.trim()}>
                Next
              </button>
            </div>
          </>
        )}

        {step === 'target' && (
          <>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
              <label>
                Target agent{' '}
                <select value={targetAgent} onChange={(e) => setTargetAgent(e.target.value)}>
                  <option value="">(none — worker replies directly)</option>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model tier{' '}
                <select value={modelTier} onChange={(e) => setModelTier(e.target.value as 'flash' | 'pro')}>
                  <option value="flash">flash</option>
                  <option value="pro">pro</option>
                </select>
              </label>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
              <button className="corp-button" onClick={() => setStep('briefing')}>
                Back
              </button>
              <button className="corp-button" onClick={submit}>
                Spawn
              </button>
            </div>
          </>
        )}
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Workers</h3>
        {workers.length === 0 && <p>No workers running right now.</p>}
        {workers.map((w) => (
          <div key={w.id} className="corp-divider-row">
            <strong>{w.id}</strong>{' '}
            <span className="corp-badge" style={{ background: STATUS_COLOR[w.status] }}>
              {w.status}
            </span>
            <div className="corp-text-muted" style={{ fontSize: '0.85rem' }}>from: {w.sourceEvent}</div>
            {w.result?.reply != null && <div style={{ fontSize: '0.85rem' }}>{String(w.result.reply)}</div>}
            {w.result?.error != null && (
              <div style={{ fontSize: '0.85rem', color: 'var(--corp-coral)' }}>{String(w.result.error)}</div>
            )}
            {w.status === 'running' && (
              <button className="corp-button" style={{ marginTop: 4 }} onClick={() => stopWorker(orgId, w.id)}>
                Stop
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
