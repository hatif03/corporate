import { useEffect, useState, type ReactNode } from 'react'
import {
  Activity as ActivityIcon,
  BookOpen,
  Brain,
  Code2,
  ListChecks,
  MessageCircleQuestion,
  Monitor as MonitorIcon,
  Settings as SettingsIcon,
  Share2,
  Wrench,
  Zap,
} from 'lucide-react'
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
import { KnowledgeBaseView } from './views/knowledge/KnowledgeBaseView'
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
  | 'knowledge'
  | 'graph'
  | 'settings'
  | 'commands'

const TAB_ICONS: Record<Tab, typeof MonitorIcon> = {
  monitor: MonitorIcon,
  tasks: ListChecks,
  askme: MessageCircleQuestion,
  activity: ActivityIcon,
  triggers: Zap,
  workers: Wrench,
  memory: Brain,
  knowledge: BookOpen,
  graph: Share2,
  settings: SettingsIcon,
  commands: Code2,
}

function AskMeTabLabel({ pendingCount }: { pendingCount: number }) {
  return (
    <>
      Ask me{pendingCount > 0 && <span className="corp-badge" style={{ background: 'var(--status-blocked)', marginLeft: 6 }}>{pendingCount}</span>}
    </>
  )
}

function SignInGate() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--corp-space-6)' }}>
      <div className="corp-panel" style={{ maxWidth: 420, textAlign: 'center', padding: 'var(--corp-space-6)' }}>
        <h1
          style={{
            margin: '0 0 var(--corp-space-4)',
            fontFamily: 'var(--corp-font-display)',
            fontSize: 'var(--corp-text-display-lg)',
            lineHeight: 'var(--corp-lh-display-lg)',
            letterSpacing: '0.04em',
          }}
        >
          Corporate
        </h1>
        <p className="corp-text-muted" style={{ margin: '0 0 var(--corp-space-5)', fontSize: 'var(--corp-text-body-md)' }}>
          A company of autonomous AI department agents, working on a live office floor —
          sign in to watch your team and dispatch new work.
        </p>
        <button className="corp-button" onClick={() => signInWithGoogle()} style={{ width: '100%' }}>
          Sign in with Google
        </button>
      </div>
    </div>
  )
}

function UserAvatar({ user }: { user: User }) {
  if (user.photoURL) {
    return (
      <img
        src={user.photoURL}
        referrerPolicy="no-referrer"
        alt=""
        style={{ width: 28, height: 28, boxShadow: 'var(--corp-border-panel)' }}
      />
    )
  }
  const initial = (user.email ?? '?').charAt(0).toUpperCase()
  return (
    <span
      className="corp-badge"
      style={{ width: 28, height: 28, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'var(--corp-sky-light)' }}
    >
      {initial}
    </span>
  )
}

function DashboardTabs({
  orgId,
  agents,
  tasks,
  tab,
  setTab,
  tabs,
}: {
  orgId: string
  agents: Agent[]
  tasks: Task[]
  tab: Tab
  setTab: (t: Tab) => void
  tabs: { id: Tab; label: ReactNode }[]
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <nav style={{ display: 'flex', gap: 'var(--corp-space-2)', flexWrap: 'wrap', marginBottom: 'var(--corp-space-3)', flexShrink: 0 }}>
        {tabs.map((t) => {
          const Icon = TAB_ICONS[t.id]
          return (
            <button key={t.id} className={`corp-button${tab === t.id ? ' corp-button--active' : ''}`} onClick={() => setTab(t.id)}>
              <Icon size={14} aria-hidden style={{ marginRight: 4, verticalAlign: -2 }} />
              {t.label}
            </button>
          )
        })}
      </nav>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        {tab === 'monitor' && <MonitorView orgId={orgId} agents={agents} />}
        {tab === 'tasks' && <TasksView tasks={tasks} />}
        {tab === 'askme' && <AskMeView orgId={orgId} tasks={tasks} />}
        {tab === 'activity' && <ActivityView orgId={orgId} />}
        {tab === 'triggers' && <TriggersView orgId={orgId} />}
        {tab === 'workers' && <WorkersView orgId={orgId} agents={agents} />}
        {tab === 'memory' && <MemoryView orgId={orgId} agents={agents} />}
        {tab === 'knowledge' && <KnowledgeBaseView orgId={orgId} agents={agents} />}
        {tab === 'graph' && <GraphView orgId={orgId} agents={agents} />}
        {tab === 'settings' && <SettingsView orgId={orgId} agents={agents} />}
        {tab === 'commands' && <CommandsView orgId={orgId} />}
      </div>
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
  const rightColumnShowsDetail = !!selectedAgent && !selectedAgent.isCeo

  function handleSelectAgent(agentId: string) {
    setSelectedAgentId((current) => (current === agentId ? null : agentId))
  }

  const tabs: { id: Tab; label: ReactNode }[] = [
    { id: 'monitor', label: 'Monitor' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'askme', label: <AskMeTabLabel pendingCount={pendingCount} /> },
    { id: 'activity', label: 'Activity' },
    { id: 'triggers', label: 'Triggers' },
    { id: 'workers', label: 'Workers' },
    { id: 'memory', label: 'Memory' },
    { id: 'knowledge', label: 'Knowledge' },
    { id: 'graph', label: 'Graph' },
    { id: 'settings', label: 'Settings' },
    { id: 'commands', label: 'Commands' },
  ]

  return (
    <div
      style={{
        height: '100vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--corp-space-5)',
        gap: 'var(--corp-space-4)',
        maxWidth: 1800,
        margin: '0 auto',
        width: '100%',
      }}
    >
      <header style={{ display: 'flex', alignItems: 'center', gap: 'var(--corp-space-4)', flexShrink: 0 }}>
        <h1 style={{ margin: 0, fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-md)', lineHeight: 'var(--corp-lh-display-md)' }}>
          Corporate
        </h1>
        <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>
          org: {ORG_ID}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 'var(--corp-space-2)' }}>
          <UserAvatar user={user} />
          <span className="corp-text-muted">{user.email}</span>
          <button className="corp-button" onClick={() => signOutUser()}>
            Sign out
          </button>
        </div>
      </header>

      <div style={{ display: 'flex', gap: 'var(--corp-space-4)', flex: 1, minHeight: 0 }}>
        <Sidebar agents={agents} selectedAgentId={selectedAgentId} onSelect={handleSelectAgent} />

        <main className="corp-panel" style={{ flex: 1, minWidth: 0, minHeight: 0, height: '100%', padding: 0, overflow: 'hidden' }}>
          <OfficeFloor agents={agents} />
        </main>

        <div className="corp-panel" style={{ width: 'var(--corp-rightcol-width)', flexShrink: 0, height: '100%', minHeight: 0, overflow: 'hidden' }}>
          {rightColumnShowsDetail ? (
            <AgentDetailView orgId={ORG_ID} agent={selectedAgent!} />
          ) : (
            <DashboardTabs orgId={ORG_ID} agents={agents} tasks={tasks} tab={tab} setTab={setTab} tabs={tabs} />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
