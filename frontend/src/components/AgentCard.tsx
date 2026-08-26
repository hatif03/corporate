// Adapted from the MIT-licensed reference design system's AgentCard, see
// /THIRD_PARTY_SKILLS.md — dimensions, selection-ring/lift mechanics, the
// CEO "surface not border weight" distinction, and the bottom-pinned gauge
// are ported as-is; data fields are our own (Agent.action/note/progress
// already exist on the model, no invented data). Portrait is our existing
// Kenney sprite frame, not procedural painting — no equivalent needed, the
// sprite art already exists as a static asset. Drag-to-reorder and the
// context-token gauge (no backing data — we don't meter LLM context
// windows) are intentionally not ported.

import { useState } from 'react'
import { PixelPanel, type AccentColorName } from './PixelPanel'
import { PixelBadge } from './PixelBadge'
import { variantForCharacter } from '../scene/office/tileset'
import type { Agent } from '../lib/types'

export interface AgentCardProps {
  agent: Agent
  selected?: boolean
  doingCount?: number
  onClick?: () => void
}

const width = 220
const height = 78

export function AgentCard({ agent, selected, doingCount = 0, onClick }: AgentCardProps) {
  const [hover, setHover] = useState(false)
  const accent = (agent.accentColor as AccentColorName) || 'sky'
  const isCeo = agent.isCeo

  // The selected card wears an ink ring OUTSIDE its border — ink-900 rather
  // than the agent's own accent so the cue is identical on every card and
  // flips correctly with the theme.
  const selectionRing = selected ? '0 0 0 2px var(--corp-ink-900)' : ''

  const progress = Math.min(1, Math.max(0, agent.progress ?? 0))
  const pct = progress * 100
  const gaugeColor = progress >= 0.875 ? 'var(--corp-coral)' : progress >= 0.75 ? 'var(--corp-lemon)' : `var(--corp-${accent})`

  const lift = (isCeo ? -2 : 0) - (hover ? 1 : 0) - (selected ? 1 : 0)
  // CEO's distinction is its SURFACE (a tinted background + accent border
  // all the way round), not a heavier rule on one edge — a one-sided accent
  // reads as a stray bar, and every card keeps the same 1px geometry so the
  // selection ring still means exactly one thing everywhere.
  const ceoSurface = isCeo
    ? { background: `var(--corp-${accent}-light)`, boxShadow: `inset 0 0 0 1px var(--corp-${accent})` }
    : {}
  const dropShadow = isCeo ? `2px 3px 0 0 rgba(26,19,32,${hover ? 0.2 : 0.14})` : hover ? '1px 2px 0 0 rgba(26,19,32,0.12)' : 'none'
  const outerShadow = [selectionRing, dropShadow === 'none' ? '' : dropShadow].filter(Boolean).join(', ') || 'none'

  const variant = variantForCharacter(agent.character, agent.department)
  const infoLine = agent.status !== 'idle' && agent.action ? agent.action : agent.description
  const noteFirstLine = (agent.note ?? '').split('\n').find((l) => l.trim()) ?? ''

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick?.()
        }
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      aria-current={selected ? 'true' : undefined}
      style={{
        width,
        minWidth: width,
        height,
        padding: 0,
        border: 'none',
        background: 'transparent',
        cursor: 'pointer',
        textAlign: 'left',
        position: 'relative',
        flexShrink: 0,
        transform: lift ? `translateY(${lift}px)` : 'none',
        boxShadow: outerShadow,
        transition: 'transform 90ms steps(2, end), box-shadow 90ms steps(2, end)',
      }}
    >
      {doingCount > 0 && (
        <span
          title={`actively working ${doingCount} task${doingCount === 1 ? '' : 's'}`}
          style={{
            position: 'absolute',
            right: -4,
            bottom: -5,
            zIndex: 2,
            width: 20,
            height: 18,
            background: 'var(--corp-sky)',
            boxShadow: 'inset 0 0 0 1px var(--corp-ink-300), 1px 2px 0 rgba(26,19,32,0.18)',
            transform: 'rotate(4deg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--corp-font-display)',
            fontSize: 8,
            color: 'var(--corp-ink-900)',
          }}
        >
          {doingCount}
        </span>
      )}
      <PixelPanel variant="default" style={{ height: '100%', padding: '6px 8px', ...ceoSurface }} noPadding>
        <div style={{ display: 'flex', gap: 8, height: '100%' }}>
          <div
            style={{
              width: 36,
              height: isCeo ? 50 : 46,
              alignSelf: 'center',
              background: isCeo ? 'var(--corp-paper-100)' : `var(--corp-${accent}-light)`,
              boxShadow: `inset 0 0 0 1px var(--corp-ink-${isCeo ? '300' : '100'})`,
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'center',
              overflow: 'hidden',
              flexShrink: 0,
            }}
          >
            <img src={variant.idle} alt="" width={32} height={32} style={{ marginTop: 4 }} />
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'space-between', minWidth: 0 }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, minWidth: 0, flex: 1 }}>
                <span
                  style={{
                    fontFamily: 'var(--corp-font-display)',
                    fontSize: 'var(--corp-text-display-sm)',
                    lineHeight: 'var(--corp-lh-display-sm)',
                    color: 'var(--corp-ink-900)',
                    flex: 1,
                    minWidth: 0,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {agent.name.toUpperCase()}
                </span>
                {isCeo && (
                  <span
                    style={{
                      fontFamily: 'var(--corp-font-display)',
                      fontSize: 7,
                      lineHeight: '11px',
                      background: `var(--corp-${accent})`,
                      color: 'var(--corp-ink-900)',
                      padding: '1px 4px 0',
                      flexShrink: 0,
                    }}
                  >
                    CEO
                  </span>
                )}
              </span>
              <PixelBadge status={agent.status} style={{ flexShrink: 0 }} />
            </div>

            <div
              title={infoLine}
              style={{
                fontSize: 11,
                lineHeight: '14px',
                color: 'var(--corp-ink-500)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {infoLine}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0, minHeight: 14 }}>
              {noteFirstLine ? (
                <span
                  title={agent.note ?? undefined}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    fontSize: 10.5,
                    lineHeight: '14px',
                    color: 'var(--corp-ink-500)',
                    fontStyle: 'italic',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {noteFirstLine}
                </span>
              ) : (
                <span style={{ flex: 1 }} />
              )}
            </div>

            <div style={{ marginTop: 'auto' }} title={`progress: ${Math.round(pct)}%`}>
              <div style={{ height: 4, width: '100%', background: 'var(--corp-cream-200)', boxShadow: 'inset 0 0 0 1px var(--corp-ink-100)', overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: gaugeColor }} />
              </div>
            </div>
          </div>
        </div>
      </PixelPanel>
    </div>
  )
}
