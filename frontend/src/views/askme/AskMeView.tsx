import { useState } from 'react'
import { answerQuestion } from '../../lib/platformClient'
import type { Task } from '../../lib/types'

function PendingQuestionCard({ orgId, task }: { orgId: string; task: Task }) {
  const [answer, setAnswer] = useState('')
  const [sending, setSending] = useState(false)
  const pendingIndex = task.humanQa.findIndex((qa) => qa.a == null && qa.dismissedAt == null)
  const question = pendingIndex >= 0 ? task.humanQa[pendingIndex] : null

  async function submit() {
    if (!answer.trim() || pendingIndex < 0) return
    setSending(true)
    try {
      await answerQuestion(orgId, task.id, answer, pendingIndex)
      setAnswer('')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="corp-panel" style={{ marginBottom: 12 }}>
      <strong>{task.title}</strong>
      <p style={{ margin: '8px 0' }}>{question?.q ?? 'This task is blocked pending a human answer.'}</p>
      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Your answer…"
        rows={2}
        style={{ width: '100%', fontFamily: 'inherit' }}
      />
      <div style={{ marginTop: 8 }}>
        <button className="corp-button" onClick={submit} disabled={sending}>
          {sending ? 'Sending…' : 'Respond & unblock'}
        </button>
      </div>
    </div>
  )
}

export function AskMeView({ orgId, tasks }: { orgId: string; tasks: Task[] }) {
  const pending = tasks.filter((t) => t.hasPendingHumanQa)

  if (pending.length === 0) {
    return (
      <div className="corp-panel">
        <p>Nothing needs your attention right now.</p>
      </div>
    )
  }

  return (
    <div>
      {pending.map((t) => (
        <PendingQuestionCard key={t.id} orgId={orgId} task={t} />
      ))}
    </div>
  )
}
