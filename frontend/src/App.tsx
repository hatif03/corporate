import { useEffect, useState } from 'react'
import { OfficeFloor } from './scene/office/OfficeFloor'
import { Sidebar } from './components/Sidebar'
import { AgentDetailView } from './views/agent-detail/AgentDetailView'
import { MonitorView } from './views/monitor/MonitorView'
import { TasksView } from './views/tasks/TasksView'
import { AskMeView } from './views/askme/AskMeView'
import { ActivityView } from './views/activity/ActivityView'
import { TriggersView } from './views/triggers/TriggersView'
import { WorkersView } from './views/workers/WorkersView'
import { MemoryView } from './views/memory/MemoryView'
import { GraphView } from './views/graph/GraphView'
import { SettingsView } from './views/settings/SettingsView'
import { CommandsView } from './views/commands/CommandsView'
import { watchAgents, watchTasks } from './lib/platformClient'
import { signInWithGoogle, signOutUser, watchAuthState } from './lib/authClient'
import type { Agent, Task } from './lib/types'
import type { User } from 'firebase/auth'

const ORG_ID = import.meta.env.VITE_ORG_ID ?? 'demo'

type Tab =
  | 'monitor'
  | 'tasks'
  | 'askme'
  | 'activity'
  | 'triggers'
  | 'workers'
  | 'memory'
  | 'graph'
  | 'settings'
  | 'commands'

function AskMeTabLabel({ pendingCount }: { pendingCount: number }) {
  return (
    <>
      Ask me{pendingCount > 0 && <span className="corp-badge" style={{ background: 'var(--status-blocked)', marginLeft: 6 }}>{pendingCount}</span>}
    </>
  )
}

function SignInGate() {
  return (
    <div style={{ padding: 48, textAlign: 'center' }}>
      <h1>Corporate</h1>
      <p>Sign in to access your company's floor.</p>
      <button className="corp-button" onClick={() => signInWithGoogle()}>
        Sign in with Google
      </button>
    </div>
  )
}

function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined) // undefined = still checking
  const [tab, setTab] = useState<Tab>('monitor')
  const [agents, setAgents] = useState<Agent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  useEffect(() => watchAuthState(setUser), [])
  useEffect(() => (user ? watchAgents(ORG_ID, setAgents) : undefined), [user])
  useEffect(() => (user ? watchTasks(ORG_ID, setTasks) : undefined), [user])

  useEffect(() => {
    if (selectedAgentId && !agents.some((a) => a.id === selectedAgentId)) setSelectedAgentId(null)
  }, [agents, selectedAgentId])

  if (user === undefined) return null // brief auth-state check on load
  if (user === null) return <SignInGate />

  const pendingCount = tasks.filter((t) => t.hasPendingHumanQa).length
  const selectedAgent = agents.find((a) => a.id === selectedAgentId)

  function handleSelectAgent(agentId: string) {
    setSelectedAgentId((current) => (current === agentId ? null : agentId))
  }

  const tabs: { id: Tab; label: React.ReactNode }[] = [
    { id: 'monitor', label: 'Monitor' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'askme', label: <AskMeTabLabel pendingCount={pendingCount} /> },
    { id: 'activity', label: 'Activity' },
    { id: 'triggers', label: 'Triggers' },
    { id: 'workers', label: 'Workers' },
    { id: 'memory', label: 'Memory' },
    { id: 'graph', label: 'Graph' },
    { id: 'settings', label: 'Settings' },
    { id: 'commands', label: 'Commands' },
  ]

  return (
    <div style={{ display: 'flex', gap: 16, padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Sidebar agents={agents} selectedAgentId={selectedAgentId} onSelect={handleSelectAgent} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <header style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginBottom: 16 }}>
          <h1 style={{ margin: 0 }}>Corporate</h1>
          <span style={{ color: '#666' }}>org: {ORG_ID}</span>
          <span style={{ color: '#666', marginLeft: 'auto' }}>{user.email}</span>
          <button className="corp-button" onClick={() => signOutUser()}>
            Sign out
          </button>
        </header>

        {selectedAgent ? <AgentDetailView orgId={ORG_ID} agent={selectedAgent} /> : <OfficeFloor agents={agents} />}

        <nav style={{ display: 'flex', gap: 8, margin: '16px 0', flexWrap: 'wrap' }}>
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
        {tab === 'workers' && <WorkersView orgId={ORG_ID} agents={agents} />}
        {tab === 'memory' && <MemoryView orgId={ORG_ID} agents={agents} />}
        {tab === 'graph' && <GraphView orgId={ORG_ID} agents={agents} />}
        {tab === 'settings' && <SettingsView orgId={ORG_ID} />}
        {tab === 'commands' && <CommandsView orgId={ORG_ID} />}
      </div>
    </div>
  )
}

export default App
