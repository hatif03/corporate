import { useEffect, useState } from 'react'
import { OfficeFloor } from './scene/office/OfficeFloor'
import { MonitorView } from './views/monitor/MonitorView'
import { TasksView } from './views/tasks/TasksView'
import { watchAgents, watchTasks } from './lib/platformClient'
import type { Agent, Task } from './lib/types'

const ORG_ID = import.meta.env.VITE_ORG_ID ?? 'demo'

type Tab = 'monitor' | 'tasks'

const TABS: { id: Tab; label: string }[] = [
  { id: 'monitor', label: 'Monitor' },
  { id: 'tasks', label: 'Tasks' },
]

function App() {
  const [tab, setTab] = useState<Tab>('monitor')
  const [agents, setAgents] = useState<Agent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])

  useEffect(() => watchAgents(ORG_ID, setAgents), [])
  useEffect(() => watchTasks(ORG_ID, setTasks), [])

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <header style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Corporate</h1>
        <span style={{ color: '#666' }}>org: {ORG_ID}</span>
      </header>

      <OfficeFloor agents={agents} />

      <nav style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            className="corp-button"
            style={{ background: tab === t.id ? 'var(--corp-accent-sky)' : undefined }}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'monitor' && <MonitorView orgId={ORG_ID} agents={agents} />}
      {tab === 'tasks' && <TasksView tasks={tasks} />}
    </div>
  )
}

export default App
