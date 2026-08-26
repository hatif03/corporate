import { useState } from 'react'

interface Endpoint {
  method: string
  path: string
  purpose: string
  body?: Record<string, unknown>
}

interface Group {
  title: string
  endpoints: Endpoint[]
}

function groupsFor(orgId: string): Group[] {
  return [
    {
      title: 'Dispatch & tasks',
      endpoints: [
        {
          method: 'POST',
          path: `/api/org/${orgId}/dispatch`,
          purpose: 'Dispatch a goal to the CEO',
          body: { text: 'Investigate the invoice backlog', attachment_data_b64: null, attachment_mime_type: null },
        },
        {
          method: 'POST',
          path: `/api/org/${orgId}/tasks/{task_id}/answer`,
          purpose: 'Answer a pending human question',
          body: { answer: 'Yes, approved', question_index: 0 },
        },
      ],
    },
    {
      title: 'Settings',
      endpoints: [
        { method: 'GET', path: `/api/org/${orgId}/settings`, purpose: 'Read the Gemini call budget' },
        {
          method: 'POST',
          path: `/api/org/${orgId}/settings`,
          purpose: 'Update the Gemini call budget',
          body: { daily_gemini_call_limit: 500 },
        },
      ],
    },
    {
      title: 'Agents',
      endpoints: [
        { method: 'POST', path: `/api/org/${orgId}/agents/{agent_id}/pause`, purpose: 'Pause an agent' },
        { method: 'POST', path: `/api/org/${orgId}/agents/{agent_id}/resume`, purpose: 'Resume an agent' },
      ],
    },
    {
      title: 'Workers',
      endpoints: [
        {
          method: 'POST',
          path: `/api/org/${orgId}/workers`,
          purpose: 'Spawn an ephemeral worker',
          body: { source_event: 'manual-test', prompt: 'Summarize open incidents', target_agent: null, model_tier: 'flash' },
        },
        { method: 'POST', path: `/api/org/${orgId}/workers/{worker_id}/stop`, purpose: 'Stop a running worker' },
      ],
    },
    {
      title: 'Triggers',
      endpoints: [
        {
          method: 'POST',
          path: `/api/org/${orgId}/triggers`,
          purpose: 'Create a trigger',
          body: {
            name: 'Nightly digest',
            type: 'schedule',
            target_agent: 'executive',
            payload_template: '{payload}',
            cron: '0 9 * * *',
          },
        },
        {
          method: 'POST',
          path: `/api/org/${orgId}/triggers/{trigger_id}/toggle?enabled=true`,
          purpose: 'Enable/disable a trigger (enabled is a query param)',
        },
        { method: 'DELETE', path: `/api/org/${orgId}/triggers/{trigger_id}`, purpose: 'Delete a trigger' },
      ],
    },
    {
      title: 'Memory',
      endpoints: [
        {
          method: 'POST',
          path: `/api/org/${orgId}/memory/search`,
          purpose: 'Semantic memory search',
          body: { query: 'fraud signals', agent_id: null, top_k: 5 },
        },
      ],
    },
    {
      title: 'Audit',
      endpoints: [
        { method: 'GET', path: `/api/org/${orgId}/audit/verify`, purpose: 'Verify the hash-chained audit log' },
      ],
    },
    {
      title: 'Integrations',
      endpoints: [
        { method: 'GET', path: `/api/org/${orgId}/integrations/catalog`, purpose: 'List integration kinds & requirements' },
        {
          method: 'POST',
          path: `/api/org/${orgId}/integrations`,
          purpose: 'Set up an integration (secret is write-only)',
          body: { kind: 'slack', base_url: null, auth_header: null, secret_value: 'xoxb-...', connected_departments: ['engineering_sre'] },
        },
        {
          method: 'POST',
          path: `/api/org/${orgId}/integrations/{integration_id}/toggle?enabled=true`,
          purpose: 'Enable/disable an integration (enabled is a query param)',
        },
      ],
    },
  ]
}

function snippetFor(e: Endpoint): string {
  const flag = e.method === 'GET' ? '' : ` -X ${e.method}`
  const bodyFlag = e.body ? ` \\\n  -H "Content-Type: application/json" \\\n  -d '${JSON.stringify(e.body, null, 2)}'` : ''
  return `curl${flag} "${e.path}"${bodyFlag}`
}

function EndpointBlock({ endpoint }: { endpoint: Endpoint }) {
  const [copied, setCopied] = useState(false)
  const snippet = snippetFor(endpoint)

  async function copy() {
    await navigator.clipboard.writeText(snippet)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: '0.85rem', color: '#555', marginBottom: 4 }}>{endpoint.purpose}</div>
      <pre style={{ background: '#f4f1ea', border: '1px solid #ddd', padding: 8, overflowX: 'auto', margin: 0 }}>
        {snippet}
      </pre>
      <button className="corp-button" style={{ marginTop: 4 }} onClick={copy}>
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}

export function CommandsView({ orgId }: { orgId: string }) {
  const groups = groupsFor(orgId)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {groups.map((g) => (
        <div key={g.title} className="corp-panel">
          <h3 style={{ marginTop: 0 }}>{g.title}</h3>
          {g.endpoints.map((e) => (
            <EndpointBlock key={`${e.method} ${e.path}`} endpoint={e} />
          ))}
        </div>
      ))}
    </div>
  )
}
