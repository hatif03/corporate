import { useEffect, useState, type ReactNode } from 'react'
import { Icon, type IconName } from './components/Icon'
import { PixelButton } from './components/PixelButton'
import { TitleBar } from './components/TitleBar'
import { SettingsModal } from './components/SettingsModal'
import { AgentStrip } from './components/AgentStrip'
import { SidebarSplitter } from './components/SidebarSplitter'
import { CompletionToast } from './components/CompletionToast'
import { CommandPalette } from './components/CommandPalette'
import { OfficeFloor } from './scene/office/OfficeFloor'
import { AgentDetailView } from './views/agent-detail/AgentDetailView'
import { MonitorView } from './views/monitor/MonitorView'
import { TasksView } from './views/tasks/TasksView'
import { AskMeView } from './views/askme/AskMeView'
import { ActivityView } from './views/activity/ActivityView'
import { TriggersView } from './views/triggers/TriggersView'
import { WorkersView } from './views/workers/WorkersView'
import { MemoryView } from './views/memory/MemoryView'
import { GraphView } from './views/graph/GraphView'
import { CommandsView } from './views/commands/CommandsView'
import { KnowledgeBaseView } from './views/knowledge/KnowledgeBaseView'
import { LandingPage } from './views/landing/LandingPage'
import { setConnectionErrorHandler, watchAgents, watchTasks } from './lib/platformClient'
import { signOutUser, watchAuthState } from './lib/authClient'
import type { Agent, Task } from './lib/types'
import type { User } from 'firebase/auth'

const ORG_ID = import.meta.env.VITE_ORG_ID ?? 'demo'
const SIDEBAR_WIDTH_KEY = 'corp.sidebarWidth'
const DEFAULT_SIDEBAR_WIDTH = 420

export type Tab = 'monitor' | 'tasks' | 'askme' | 'activity' | 'triggers' | 'workers' | 'memory' | 'knowledge' | 'graph' | 'commands'

const TAB_ICONS: Record<Tab, IconName> = {
  monitor: 'monitor',
  tasks: 'list',
  askme: 'question',
  activity: 'activity',
  triggers: 'zap',
  workers: 'wrench',
  memory: 'brain',
  knowledge: 'book',
  graph: 'share',
  commands: 'code',
}

function loadSidebarWidth(): number {
  try {
    const raw = window.localStorage.getItem(SIDEBAR_WIDTH_KEY)
    const n = raw ? Number(raw) : NaN
    return Number.isFinite(n) ? n : DEFAULT_SIDEBAR_WIDTH
  } catch {
    return DEFAULT_SIDEBAR_WIDTH
  }
}

function AskMeTabLabel({ pendingCount }: { pendingCount: number }) {
  return (
    <>
      Ask me{pendingCount > 0 && <span className="corp-badge" style={{ background: 'var(--status-blocked)', marginLeft: 6 }}>{pendingCount}</span>}
    </>
  )
}

function DashboardTabs({
  orgId,
  agents,
  tasks,
  tab,
  setTab,
  tabs,
  onSelectAgent,
}: {
  orgId: string
  agents: Agent[]
  tasks: Task[]
  tab: Tab
  setTab: (t: Tab) => void
  tabs: { id: Tab; label: ReactNode }[]
  onSelectAgent: (agentId: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <nav style={{ display: 'flex', gap: 'var(--corp-space-2)', flexWrap: 'wrap', marginBottom: 'var(--corp-space-3)', flexShrink: 0 }}>
        {tabs.map((t) => (
          <PixelButton key={t.id} variant={tab === t.id ? 'primary' : 'secondary'} size="sm" onClick={() => setTab(t.id)}>
            <Icon name={TAB_ICONS[t.id]} style={{ marginRight: 4 }} />
            {t.label}
          </PixelButton>
        ))}
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
        {tab === 'graph' && <GraphView orgId={orgId} agents={agents} onSelectAgent={onSelectAgent} />}
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
  const [sidebarWidth, setSidebarWidth] = useState(loadSidebarWidth)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [focusMode, setFocusMode] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  useEffect(() => {
    setConnectionErrorHandler((err) => setConnectionError(err.message))
  }, [])
  useEffect(() => watchAuthState(setUser), [])
  useEffect(
    () => (user ? watchAgents(ORG_ID, (a) => { setAgents(a); setConnectionError(null) }) : undefined),
    [user],
  )
  useEffect(
    () => (user ? watchTasks(ORG_ID, (t) => { setTasks(t); setConnectionError(null) }) : undefined),
    [user],
  )

  useEffect(() => {
    if (selectedAgentId && !agents.some((a) => a.id === selectedAgentId)) setSelectedAgentId(null)
  }, [agents, selectedAgentId])

  function updateSidebarWidth(px: number) {
    setSidebarWidth(px)
    try {
      window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(px))
    } catch {
      /* noop */
    }
  }

  if (user === undefined) return null // brief auth-state check on load
  if (user === null) return <LandingPage />

  const pendingCount = tasks.filter((t) => t.hasPendingHumanQa).length
  const selectedAgent = agents.find((a) => a.id === selectedAgentId)
  // The CEO used to be excluded here, which meant a CEO-proposed pending
  // skill (it has the same tools as every department, factory.py's
  // _CEO_TOOLS) was permanently unreachable — Terminal/Messages/Skills all
  // already work generically for any agent id, CEO included.
  const rightPanelShowsDetail = !!selectedAgent

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
    { id: 'commands', label: 'Commands' },
  ]

  return (
    <div style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <TitleBar
        orgId={ORG_ID}
        user={user}
        onOpenSettings={() => setSettingsOpen(true)}
        onSignOut={() => signOutUser()}
        focusMode={focusMode}
        onToggleFocusMode={() => setFocusMode((f) => !f)}
      />

      {connectionError && (
        <div
          className="corp-badge"
          style={{
            background: 'var(--status-blocked)',
            borderRadius: 0,
            textAlign: 'center',
            padding: 'var(--corp-space-1)',
            fontSize: 'var(--corp-text-body-sm)',
          }}
        >
          Connection lost — retrying… ({connectionError})
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, minHeight: 0, display: 'flex', padding: 'var(--corp-space-4)', overflow: 'hidden' }}>
          {!focusMode && (
            <>
              <main style={{ flex: 1, minWidth: 0, position: 'relative', overflow: 'hidden' }}>
                <OfficeFloor agents={agents} orgId={ORG_ID} onSelectAgent={handleSelectAgent} />
              </main>

              <SidebarSplitter width={sidebarWidth} onChange={updateSidebarWidth} viewportWidth={window.innerWidth} />
            </>
          )}

          <div className="corp-panel" style={{ width: focusMode ? '100%' : sidebarWidth, flexShrink: 0, minHeight: 0, overflow: 'hidden' }}>
            {rightPanelShowsDetail ? (
              <AgentDetailView orgId={ORG_ID} agent={selectedAgent!} />
            ) : (
              <DashboardTabs orgId={ORG_ID} agents={agents} tasks={tasks} tab={tab} setTab={setTab} tabs={tabs} onSelectAgent={handleSelectAgent} />
            )}
          </div>
        </div>

        <AgentStrip agents={agents} tasks={tasks} selectedAgentId={selectedAgentId} onSelect={handleSelectAgent} />
      </div>

      {settingsOpen && <SettingsModal orgId={ORG_ID} agents={agents} onClose={() => setSettingsOpen(false)} />}
      <CompletionToast tasks={tasks} />
      <CommandPalette
        orgId={ORG_ID}
        agents={agents}
        onSelectAgent={handleSelectAgent}
        onGoToTab={setTab}
        onOpenSettings={() => setSettingsOpen(true)}
        onToggleFocusMode={() => setFocusMode((f) => !f)}
        onSignOut={() => signOutUser()}
      />
    </div>
  )
}

export default App
