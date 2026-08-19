// Mirrors backend/app/models/*.py — field names are camelCase to match what
// the backend actually writes to Firestore (see the model_config note in
// agent.py/task.py/message.py). Keep these two in sync by hand for now; see
// /shared/schema/ for the source-of-truth JSON Schemas once those exist.

export type AgentStatus =
  | 'idle'
  | 'thinking'
  | 'working'
  | 'waiting'
  | 'blocked'
  | 'success'
  | 'ghost'
  | 'compacting'
  | 'looping'
  | 'typing'

export type CarryingToken = 'none' | 'file' | 'bash' | 'web' | 'grep' | 'mcp' | 'todo'

export interface Agent {
  id: string
  name: string
  character: string
  avatarSpriteId: string
  department: string
  accentColor: string
  description: string
  goal?: string | null
  note?: string | null
  status: AgentStatus
  action: string
  progress: number
  currentStation?: string | null
  carrying: CarryingToken
  isCeo: boolean
  provider: string
  model: string
}

export type TaskStatus = 'todo' | 'doing' | 'blocked' | 'done'

export interface HumanQA {
  q: string
  a?: string | null
  askedBy: string
  answeredAt?: string | null
  dismissedAt?: string | null
}

export interface Task {
  id: string
  title: string
  description: string
  taskType: string
  status: TaskStatus
  assignee?: string | null
  dependsOn: string[]
  humanQa: HumanQA[]
  hasPendingHumanQa: boolean
  result?: Record<string, unknown> | null
  createdBy: string
  priority: number
}
