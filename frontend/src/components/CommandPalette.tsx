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

interface Command {
  id: string
  label: string
  hint?: string
  run: () => void
}

export function CommandPalette({ orgId, agents, onSelectAgent }: { orgId: string; agents: Agent[]; onSelectAgent: (agentId: string) => void }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [dispatchText, setDispatchText] = useState('')
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
    else setQuery('')
  }, [open])

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = []
    for (const a of agents) {
      list.push({ id: `open-${a.id}`, label: `Open ${a.name}`, hint: a.department, run: () => onSelectAgent(a.id) })
      list.push({
        id: `toggle-${a.id}`,
        label: `${a.paused ? 'Resume' : 'Pause'} ${a.name}`,
        run: () => void (a.paused ? resumeAgent(orgId, a.id) : pauseAgent(orgId, a.id)),
      })
    }
    return list
  }, [agents, orgId, onSelectAgent])

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))

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
              value={dispatchText || query}
              onChange={(e) => (dispatchText ? setDispatchText(e.target.value) : setQuery(e.target.value))}
              placeholder={dispatchText ? 'Dispatch a goal to the CEO…' : 'Type a command, or start typing a goal to dispatch…'}
              style={{ flex: 1 }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && dispatchText.trim()) {
                  void dispatchGoal(orgId, dispatchText.trim())
                  setDispatchText('')
                  setOpen(false)
                }
              }}
            />
            {!dispatchText && (
              <button className="corp-button" onClick={() => setDispatchText(query)} title="Dispatch this as a goal instead">
                <Icon name="arrow-right" />
              </button>
            )}
          </div>
          {!dispatchText && (
            <div style={{ maxHeight: 320, overflowY: 'auto' }}>
              {filtered.length === 0 && <p className="corp-text-muted" style={{ fontSize: '0.85rem' }}>No matching command — press the arrow to dispatch this text as a goal instead.</p>}
              {filtered.slice(0, 30).map((c) => (
                <button
                  key={c.id}
                  className="corp-button"
                  style={{ width: '100%', textAlign: 'left', marginBottom: 4 }}
                  onClick={() => {
                    c.run()
                    setOpen(false)
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
