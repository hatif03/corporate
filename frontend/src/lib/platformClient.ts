// The single data-access layer: every view goes through this, never
// Firestore/REST directly (mirrors the backend's platform-client convention
// — see docs/system_prompt.md).

import { collection, limit, onSnapshot, orderBy, query } from 'firebase/firestore'
import { db } from './firebase'
import { getIdToken } from './authClient'
import type { Agent, Task, Trigger, TriggerType, Worker } from './types'

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

export interface ActivityEntry {
  id: string
  ts: string
  agentId: string
  type: string
  message: string
}

export interface MessageEntry {
  id: string
  from: string
  to: string
  act: string
  subject: string
  createdAt: string
}

export function watchMessages(
  orgId: string,
  onChange: (messages: MessageEntry[]) => void,
  limitCount = 200,
): () => void {
  const q = query(orgCollection(orgId, 'messages'), orderBy('createdAt', 'desc'), limit(limitCount))
  return onSnapshot(q, (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as MessageEntry))
  })
}

export function watchActivity(
  orgId: string,
  onChange: (entries: ActivityEntry[]) => void,
  limitCount = 100,
): () => void {
  const q = query(orgCollection(orgId, 'activity_log'), orderBy('ts', 'desc'), limit(limitCount))
  return onSnapshot(q, (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as ActivityEntry))
  })
}

export interface MemoryEntry {
  id: string
  text: string
  kind: string
  createdAt: string
}

export function watchAgentMemory(
  orgId: string,
  agentId: string,
  onChange: (entries: MemoryEntry[]) => void,
  limitCount = 50,
): () => void {
  const q = query(
    collection(db, 'orgs', orgId, 'agents', agentId, 'memory'),
    orderBy('createdAt', 'desc'),
    limit(limitCount),
  )
  return onSnapshot(q, (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as MemoryEntry))
  })
}

export interface MemoryHit {
  agentId: string
  memoryId: string
  text: string
  score: number
}

export async function searchMemory(
  orgId: string,
  query: string,
  agentId?: string,
  topK = 5,
): Promise<MemoryHit[]> {
  const result = (await post(`/api/org/${orgId}/memory/search`, {
    query,
    agent_id: agentId ?? null,
    top_k: topK,
  })) as { hits: MemoryHit[] }
  return result.hits
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

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getIdToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function post(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

async function del(path: string): Promise<unknown> {
  const res = await fetch(`${BACKEND_URL}${path}`, { method: 'DELETE', headers: await authHeaders() })
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

export function watchTriggers(orgId: string, onChange: (triggers: Trigger[]) => void): () => void {
  return onSnapshot(orgCollection(orgId, 'triggers'), (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as Trigger))
  })
}

export function createTrigger(
  orgId: string,
  input: { name: string; type: TriggerType; target_agent: string; payload_template: string; cron?: string },
): Promise<Trigger> {
  return post(`/api/org/${orgId}/triggers`, input) as Promise<Trigger>
}

export function toggleTrigger(orgId: string, triggerId: string, enabled: boolean): Promise<unknown> {
  return post(`/api/org/${orgId}/triggers/${triggerId}/toggle?enabled=${enabled}`, {})
}

export function deleteTrigger(orgId: string, triggerId: string): Promise<unknown> {
  return del(`/api/org/${orgId}/triggers/${triggerId}`)
}

export function watchWorkers(orgId: string, onChange: (workers: Worker[]) => void): () => void {
  return onSnapshot(orgCollection(orgId, 'workers'), (snap) => {
    onChange(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as Worker))
  })
}

export function spawnWorker(orgId: string, sourceEvent: string, prompt: string): Promise<{ worker_id: string }> {
  return post(`/api/org/${orgId}/workers`, { source_event: sourceEvent, prompt }) as Promise<{ worker_id: string }>
}

export function stopWorker(orgId: string, workerId: string): Promise<unknown> {
  return post(`/api/org/${orgId}/workers/${workerId}/stop`, {})
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
