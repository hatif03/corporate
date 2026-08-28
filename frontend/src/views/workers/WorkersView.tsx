import { useEffect, useState } from 'react'
import { Collapsible } from '../../components/Collapsible'
import { spawnWorker, stopWorker, watchAgentTrace, watchWorkers } from '../../lib/platformClient'
import type { Agent, Worker } from '../../lib/types'

// Workers run through the same ADK Runner/session machinery as any other
// agent (session id === worker id, see app/services/workers.py), so the
// existing trace subcollection under agents/{id}/trace already fills in
// for them — no new backend collection or endpoint needed, just this reuse.
function WorkerTrace({ orgId, workerId }: { orgId: string; workerId: string }) {
  const [lines, setLines] = useState<string[]>([])
  useEffect(() => watchAgentTrace(orgId, workerId, setLines), [orgId, workerId])
  if (lines.length === 0) return <p className="corp-text-muted" style={{ fontSize: '0.8rem' }}>No trace yet.</p>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {lines.map((l, i) => (
        <div key={i} className="corp-text-muted" style={{ fontSize: '0.8rem', fontFamily: 'var(--corp-font-mono)' }}>
          {l}
        </div>
      ))}
    </div>
  )
}

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
  const [error, setError] = useState<string | null>(null)
  const [spawning, setSpawning] = useState(false)

  useEffect(() => watchWorkers(orgId, setWorkers), [orgId])

  async function submit() {
    if (!prompt.trim()) return
    setSpawning(true)
    setError(null)
    try {
      await spawnWorker(orgId, 'manual-test', prompt, targetAgent || null, modelTier)
      setPrompt('')
      setTargetAgent('')
      setModelTier('flash')
      setStep('briefing')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSpawning(false)
    }
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
              <button className="corp-button" onClick={submit} disabled={spawning}>
                {spawning ? 'Spawning…' : 'Spawn'}
              </button>
            </div>
            {error && <p style={{ color: 'var(--corp-coral)', marginTop: 8 }}>{error}</p>}
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
            {w.cloudRunJobExecutionId && (
              <div className="corp-text-muted" style={{ fontSize: '0.8rem' }}>job: {w.cloudRunJobExecutionId}</div>
            )}
            {w.result?.reply != null && <div style={{ fontSize: '0.85rem' }}>{String(w.result.reply)}</div>}
            {w.result?.error != null && (
              <div style={{ fontSize: '0.85rem', color: 'var(--corp-coral)' }}>{String(w.result.error)}</div>
            )}
            {w.status === 'running' && (
              <button className="corp-button" style={{ marginTop: 4 }} onClick={() => stopWorker(orgId, w.id)}>
                Stop
              </button>
            )}
            <Collapsible title={<span style={{ fontSize: '0.8rem' }}>Trace</span>}>
              <WorkerTrace orgId={orgId} workerId={w.id} />
            </Collapsible>
          </div>
        ))}
      </div>
    </div>
  )
}
