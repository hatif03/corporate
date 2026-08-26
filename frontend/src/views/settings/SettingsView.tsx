import { useEffect, useState } from 'react'
import { Icon } from '../../components/Icon'
import {
  createIntegration,
  getIntegrationCatalog,
  getSettings,
  listAccessRequests,
  listIntegrations,
  resolveAccessRequest,
  updateIntegrationDepartments,
  updateSettings,
  type AccessRequestEntry,
  type IntegrationConfig,
  type IntegrationTemplate,
} from '../../lib/platformClient'
import type { Agent } from '../../lib/types'

function ConnectForm({ orgId, kind, template, onConnected }: { orgId: string; kind: string; template: IntegrationTemplate; onConnected: () => void }) {
  const [secretValue, setSecretValue] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const needsSecret = template.auth_type !== 'none'

  async function connect() {
    setBusy(true)
    try {
      await createIntegration(orgId, {
        kind,
        base_url: baseUrl.trim() || null,
        secret_value: needsSecret ? secretValue.trim() : null,
      })
      setSecretValue('')
      onConnected()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
      {needsSecret && (
        <input
          type="password"
          placeholder={template.secret_label}
          value={secretValue}
          onChange={(e) => setSecretValue(e.target.value)}
        />
      )}
      <input placeholder={`Base URL (default: ${template.default_base_url})`} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button className="corp-button" onClick={connect} disabled={busy || (needsSecret && !secretValue.trim())}>
          {busy ? 'Connecting…' : 'Connect'}
        </button>
        {template.docs_url && (
          <a href={template.docs_url} target="_blank" rel="noreferrer" className="corp-text-muted" style={{ fontSize: '0.8rem' }}>
            Where do I find this?
          </a>
        )}
      </div>
    </div>
  )
}

function ConnectedApps({ orgId, agents }: { orgId: string; agents: Agent[] }) {
  const departments = agents.filter((a) => !a.isCeo)
  const [catalog, setCatalog] = useState<Record<string, IntegrationTemplate>>({})
  const [integrations, setIntegrations] = useState<IntegrationConfig[]>([])
  const [requests, setRequests] = useState<AccessRequestEntry[]>([])
  const [connectingKind, setConnectingKind] = useState<string | null>(null)

  async function refresh() {
    const [c, i, r] = await Promise.all([getIntegrationCatalog(orgId), listIntegrations(orgId), listAccessRequests(orgId)])
    setCatalog(c)
    setIntegrations(i)
    setRequests(r)
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId])

  async function toggleDept(integration: IntegrationConfig, deptId: string) {
    const has = integration.connectedDepartments.includes(deptId)
    const next = has
      ? integration.connectedDepartments.filter((d) => d !== deptId)
      : [...integration.connectedDepartments, deptId]
    await updateIntegrationDepartments(orgId, integration.id, next)
    await refresh()
  }

  async function resolve(requestId: string, approve: boolean) {
    await resolveAccessRequest(orgId, requestId, approve)
    await refresh()
  }

  const pending = requests.filter((r) => r.status === 'pending')
  const byKind = new Map(integrations.map((i) => [i.kind, i]))

  return (
    <>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Connected apps</h3>
        <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
          Every app this org can connect. Configured apps show which departments may call them — leaving a row's
          department list empty means unrestricted, every department may use it.
        </p>
        {Object.entries(catalog).map(([kind, template]) => {
          const integ = byKind.get(kind)
          return (
            <div key={kind} className="corp-divider-row">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ textTransform: 'capitalize' }}>{kind}</strong>
                {integ ? (
                  <span className="corp-badge" style={{ background: integ.enabled ? 'var(--corp-mint-light)' : undefined }}>
                    {integ.enabled ? 'connected' : 'disabled'}
                  </span>
                ) : connectingKind === kind ? (
                  <button className="corp-button" onClick={() => setConnectingKind(null)}>
                    Cancel
                  </button>
                ) : (
                  <button className="corp-button" onClick={() => setConnectingKind(kind)}>
                    Connect
                  </button>
                )}
              </div>

              {integ ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                  {departments.map((d) => {
                    const active = integ.connectedDepartments.includes(d.department)
                    return (
                      <button
                        key={d.department}
                        className="corp-button"
                        style={{ fontSize: '0.8rem', opacity: integ.connectedDepartments.length === 0 || active ? 1 : 0.5 }}
                        onClick={() => toggleDept(integ, d.department)}
                      >
                        {active ? '✓ ' : ''}
                        {d.name}
                      </button>
                    )
                  })}
                </div>
              ) : connectingKind === kind ? (
                <ConnectForm
                  orgId={orgId}
                  kind={kind}
                  template={template}
                  onConnected={() => {
                    setConnectingKind(null)
                    void refresh()
                  }}
                />
              ) : null}
            </div>
          )
        })}
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Pending access requests</h3>
        {pending.length === 0 && <p className="corp-text-muted">No pending requests.</p>}
        {pending.map((r) => (
          <div key={r.id} className="corp-divider-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>
              <strong>{r.departmentId}</strong> wants access to <strong>{r.integrationId}</strong>
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="corp-button" title="Approve" onClick={() => resolve(r.id, true)}>
                <Icon name="check" />
              </button>
              <button className="corp-button" title="Deny" onClick={() => resolve(r.id, false)}>
                <Icon name="x" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

export function SettingsView({ orgId, agents }: { orgId: string; agents: Agent[] }) {
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

      <ConnectedApps orgId={orgId} agents={agents} />
    </div>
  )
}
