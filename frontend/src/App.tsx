import { useEffect, useState } from 'react'
import { OfficeFloor } from './scene/office/OfficeFloor'
import { MonitorView } from './views/monitor/MonitorView'
import { TasksView } from './views/tasks/TasksView'
import { AskMeView } from './views/askme/AskMeView'
import { ActivityView } from './views/activity/ActivityView'
import { TriggersView } from './views/triggers/TriggersView'
import { WorkersView } from './views/workers/WorkersView'
import { MemoryView } from './views/memory/MemoryView'
import { GraphView } from './views/graph/GraphView'
import { watchAgents, watchTasks } from './lib/platformClient'
import type { Agent, Task } from './lib/types'

const ORG_ID = import.meta.env.VITE_ORG_ID ?? 'demo'

type Tab = 'monitor' | 'tasks' | 'askme' | 'activity' | 'triggers' | 'workers' | 'memory' | 'graph'

function AskMeTabLabel({ pendingCount }: { pendingCount: number }) {
  return (
    <>
      Ask me{pendingCount > 0 && <span className="corp-badge" style={{ background: 'var(--status-blocked)', marginLeft: 6 }}>{pendingCount}</span>}
    </>
  )
}

function App() {
  const [tab, setTab] = useState<Tab>('monitor')
  const [agents, setAgents] = useState<Agent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])

  useEffect(() => watchAgents(ORG_ID, setAgents), [])
  useEffect(() => watchTasks(ORG_ID, setTasks), [])

  const pendingCount = tasks.filter((t) => t.hasPendingHumanQa).length

  const tabs: { id: Tab; label: React.ReactNode }[] = [
    { id: 'monitor', label: 'Monitor' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'askme', label: <AskMeTabLabel pendingCount={pendingCount} /> },
    { id: 'activity', label: 'Activity' },
    { id: 'triggers', label: 'Triggers' },
    { id: 'workers', label: 'Workers' },
    { id: 'memory', label: 'Memory' },
    { id: 'graph', label: 'Graph' },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <header style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Corporate</h1>
        <span style={{ color: '#666' }}>org: {ORG_ID}</span>
      </header>

      <OfficeFloor agents={agents} />

      <nav style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        {tabs.map((t) => (
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
      {tab === 'askme' && <AskMeView orgId={ORG_ID} tasks={tasks} />}
      {tab === 'activity' && <ActivityView orgId={ORG_ID} />}
      {tab === 'triggers' && <TriggersView orgId={ORG_ID} />}
      {tab === 'workers' && <WorkersView orgId={ORG_ID} />}
      {tab === 'memory' && <MemoryView orgId={ORG_ID} agents={agents} />}
      {tab === 'graph' && <GraphView orgId={ORG_ID} agents={agents} />}
    </div>
  )
}

export default App
