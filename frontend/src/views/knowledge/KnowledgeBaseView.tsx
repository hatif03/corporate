import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { createKnowledgeDoc, deleteKnowledgeDoc, listKnowledgeDocs, type KnowledgeDoc } from '../../lib/platformClient'
import type { Agent } from '../../lib/types'

export function KnowledgeBaseView({ orgId, agents }: { orgId: string; agents: Agent[] }) {
  const departments = agents.filter((a) => !a.isCeo)
  const [selectedDept, setSelectedDept] = useState<string>('')
  const [docs, setDocs] = useState<KnowledgeDoc[]>([])
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (departments.length > 0 && !selectedDept) setSelectedDept(departments[0].department)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [departments.length])

  async function refresh(dept: string) {
    setLoading(true)
    try {
      setDocs(await listKnowledgeDocs(orgId, dept))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedDept) void refresh(selectedDept)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId, selectedDept])

  function onFileChosen(file: File) {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setText(reader.result)
        if (!title) setTitle(file.name)
      }
    }
    reader.readAsText(file)
  }

  async function save() {
    if (!selectedDept || !title.trim() || !text.trim()) return
    setSaving(true)
    try {
      await createKnowledgeDoc(orgId, selectedDept, title.trim(), text)
      setTitle('')
      setText('')
      await refresh(selectedDept)
    } finally {
      setSaving(false)
    }
  }

  async function remove(docId: string) {
    await deleteKnowledgeDoc(orgId, selectedDept, docId)
    await refresh(selectedDept)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Knowledge base</h3>
        <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>
          Upload documents for a department's agents to ground their answers on. Once a department has at least
          one uploaded document, it's used instead of that department's built-in starter corpus.
        </p>
        <select value={selectedDept} onChange={(e) => setSelectedDept(e.target.value)}>
          {departments.map((a) => (
            <option key={a.department} value={a.department}>
              {a.name}
            </option>
          ))}
        </select>

        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <input placeholder="Document title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <textarea
            placeholder="Paste text, or choose a file below"
            rows={6}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) onFileChosen(file)
              }}
            />
            <button className="corp-button" onClick={save} disabled={saving || !title.trim() || !text.trim()}>
              {saving ? 'Saving…' : 'Upload'}
            </button>
          </div>
        </div>
      </div>

      <div className="corp-panel">
        <h3 style={{ marginTop: 0 }}>Documents{selectedDept ? ` — ${departments.find((a) => a.department === selectedDept)?.name}` : ''}</h3>
        {loading && <p className="corp-text-muted">Loading…</p>}
        {!loading && docs.length === 0 && <p className="corp-text-muted">No documents uploaded yet — using the static starter corpus.</p>}
        {docs.map((d) => (
          <div key={d.id} className="corp-divider-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
            <div>
              <strong>{d.title}</strong>
              <div style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>{d.text.length > 300 ? `${d.text.slice(0, 300)}…` : d.text}</div>
            </div>
            <button className="corp-button" title="Delete" onClick={() => remove(d.id)}>
              <Trash2 size={14} aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
