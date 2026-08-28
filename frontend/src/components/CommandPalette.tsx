// Evolves CommandsView from copy-paste curl snippets into an actual
// quick-action launcher — calls platformClient functions directly instead
// of only showing the equivalent curl command. Scoped to actions backed by
// data already loaded in App.tsx (agents) — trigger actions stay in
// TriggersView rather than pulling in a second subscription just for the
// palette.

import { useEffect, useMemo, useRef, useState } from 'react'
import { Icon } from './Icon'
import { PixelPanel } from './PixelPanel'
import { dispatchGoal, pauseAgent, resumeAgent } from '../lib/platformClient'
import type { Agent } from '../lib/types'
import type { Tab } from '../App'

interface Command {
  id: string
  label: string
  hint?: string
  run: () => void
}

const TAB_LABELS: { id: Tab; label: string }[] = [
  { id: 'monitor', label: 'Monitor' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'askme', label: 'Ask me' },
  { id: 'activity', label: 'Activity' },
  { id: 'triggers', label: 'Triggers' },
  { id: 'workers', label: 'Workers' },
  { id: 'memory', label: 'Memory' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'graph', label: 'Graph' },
  { id: 'commands', label: 'Commands' },
]

export function CommandPalette({
  orgId,
  agents,
  onSelectAgent,
  onGoToTab,
  onOpenSettings,
  onToggleFocusMode,
  onSignOut,
}: {
  orgId: string
  agents: Agent[]
  onSelectAgent: (agentId: string) => void
  onGoToTab: (tab: Tab) => void
  onOpenSettings: () => void
  onToggleFocusMode: () => void
  onSignOut: () => void
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  // A real boolean, not `dispatchText`'s own truthiness — the old version
  // conflated "in dispatch mode" with "dispatch text is non-empty," which
  // meant switching into dispatch mode with nothing typed yet was
  // impossible (the UI would just silently stay in command-search mode).
  const [dispatchMode, setDispatchMode] = useState(false)
  const [dispatchText, setDispatchText] = useState('')
  const [highlighted, setHighlighted] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 0)
    else {
      setQuery('')
      setDispatchMode(false)
      setDispatchText('')
    }
  }, [open])

  function enterDispatchMode(initialText = '') {
    setDispatchText(initialText)
    setDispatchMode(true)
  }

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = []
    for (const t of TAB_LABELS) {
      list.push({ id: `tab-${t.id}`, label: `Go to ${t.label}`, run: () => onGoToTab(t.id) })
    }
    list.push({ id: 'open-settings', label: 'Open Settings', run: onOpenSettings })
    list.push({ id: 'toggle-focus', label: 'Toggle Focus Mode', run: onToggleFocusMode })
    list.push({ id: 'sign-out', label: 'Sign out', run: onSignOut })
    list.push({ id: 'dispatch', label: 'Dispatch a goal', hint: 'to the CEO', run: () => enterDispatchMode() })
    for (const a of agents) {
      list.push({ id: `open-${a.id}`, label: `Open ${a.name}`, hint: a.department, run: () => onSelectAgent(a.id) })
      list.push({
        id: `toggle-${a.id}`,
        label: `${a.paused ? 'Resume' : 'Pause'} ${a.name}`,
        run: () => void (a.paused ? resumeAgent(orgId, a.id) : pauseAgent(orgId, a.id)),
      })
    }
    return list
  }, [agents, orgId, onSelectAgent, onGoToTab, onOpenSettings, onToggleFocusMode, onSignOut])

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))

  useEffect(() => {
    setHighlighted(0)
  }, [query])

  function runHighlighted() {
    const cmd = filtered[highlighted]
    if (cmd) {
      cmd.run()
      if (cmd.id !== 'dispatch') setOpen(false)
    }
  }

  if (!open) return null

  return (
    <div
      onClick={() => setOpen(false)}
      style={{ position: 'fixed', inset: 0, background: 'rgba(26, 19, 32, 0.45)', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '15vh', zIndex: 250 }}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(480px, 92vw)' }}>
        <PixelPanel variant="dialog">
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              ref={inputRef}
              value={dispatchMode ? dispatchText : query}
              onChange={(e) => (dispatchMode ? setDispatchText(e.target.value) : setQuery(e.target.value))}
              placeholder={dispatchMode ? 'Dispatch a goal to the CEO…' : 'Type a command, or start typing a goal to dispatch…'}
              style={{ flex: 1 }}
              onKeyDown={(e) => {
                if (dispatchMode) {
                  if (e.key === 'Enter' && dispatchText.trim()) {
                    void dispatchGoal(orgId, dispatchText.trim())
                    setOpen(false)
                  }
                  return
                }
                if (e.key === 'ArrowDown') {
                  e.preventDefault()
                  setHighlighted((h) => Math.min(h + 1, Math.max(filtered.length - 1, 0)))
                } else if (e.key === 'ArrowUp') {
                  e.preventDefault()
                  setHighlighted((h) => Math.max(h - 1, 0))
                } else if (e.key === 'Enter') {
                  e.preventDefault()
                  runHighlighted()
                }
              }}
            />
            {!dispatchMode && (
              <button className="corp-button" onClick={() => enterDispatchMode(query)} title="Dispatch this as a goal instead">
                <Icon name="arrow-right" />
              </button>
            )}
          </div>
          {!dispatchMode && (
            <div style={{ maxHeight: 320, overflowY: 'auto' }}>
              {filtered.length === 0 && <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>No matching command — press the arrow to dispatch this text as a goal instead.</p>}
              {filtered.slice(0, 30).map((c, i) => (
                <button
                  key={c.id}
                  className={`corp-button${i === highlighted ? ' corp-button--active' : ''}`}
                  style={{ width: '100%', textAlign: 'left', marginBottom: 4 }}
                  onMouseEnter={() => setHighlighted(i)}
                  onClick={() => {
                    c.run()
                    if (c.id !== 'dispatch') setOpen(false)
                  }}
                >
                  {c.label}
                  {c.hint && <span className="corp-text-muted" style={{ marginLeft: 8, fontSize: '0.8rem' }}>{c.hint}</span>}
                </button>
              ))}
            </div>
          )}
        </PixelPanel>
      </div>
    </div>
  )
}
