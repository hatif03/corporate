// The single data-access layer: every view goes through this, never
// Firestore/REST directly (mirrors the backend's platform-client convention
// — see docs/system_prompt.md).

import { collection, onSnapshot, orderBy, query } from 'firebase/firestore'
import { db } from './firebase'
import type { Agent, Task } from './types'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

function orgCollection(orgId: string, name: string) {
  return collection(db, 'orgs', orgId, name)
}

export function watchAgents(orgId: string, onChange: (agents: Agent[]) => void): () => void {
  return onSnapshot(orgCollection(orgId, 'agents'), (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as Agent))
  })
}

export function watchTasks(orgId: string, onChange: (tasks: Task[]) => void): () => void {
  const q = query(orgCollection(orgId, 'tasks'), orderBy('createdAt', 'desc'))
  return onSnapshot(q, (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as Task))
  })
}

export function watchAgentTrace(
  orgId: string,
  agentId: string,
  onChange: (lines: string[]) => void,
): () => void {
  const q = query(collection(db, 'orgs', orgId, 'agents', agentId, 'trace'), orderBy('ts', 'asc'))
  return onSnapshot(q, (snap) => {
    onChange(snap.docs.map((d) => d.data().line as string))
  })
}

async function post(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

export function dispatchGoal(orgId: string, text: string): Promise<unknown> {
  return post(`/api/org/${orgId}/dispatch`, { text })
}

export function answerQuestion(
  orgId: string,
  taskId: string,
  answer: string,
  questionIndex = 0,
): Promise<unknown> {
  return post(`/api/org/${orgId}/tasks/${taskId}/answer`, { answer, question_index: questionIndex })
}
