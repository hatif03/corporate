// Ported from the MIT-licensed reference design system, see
// /THIRD_PARTY_SKILLS.md. Token names adapted (--cth-status-* -> --status-*,
// --cth-* -> --corp-*), StatusKind -> our own AgentStatus, otherwise
// verbatim including the status->label remapping.

import type { CSSProperties } from 'react'
import type { AgentStatus } from '../lib/types'

export interface PixelBadgeProps {
  status: AgentStatus
  label?: string
  style?: CSSProperties
}

const colorByStatus: Record<AgentStatus, string> = {
  idle: 'var(--status-idle)',
  thinking: 'var(--status-thinking)',
  working: 'var(--status-working)',
  waiting: 'var(--status-waiting)',
  blocked: 'var(--status-blocked)',
  success: 'var(--status-success)',
  ghost: 'var(--status-ghost)',
  compacting: 'var(--status-compacting)',
  looping: 'var(--status-looping)',
  typing: 'var(--status-typing)',
}

// "blocked" is reserved for a task waiting on a human — it reads as "needs
// you" rather than the raw status name. "typing" means a human has unsent
// input holding that agent's dispatch, so it reads as "your draft", not
// "the agent is typing".
const labelByStatus: Record<AgentStatus, string> = {
  idle: 'idle',
  thinking: 'working',
  working: 'working',
  waiting: 'waiting',
  blocked: 'needs you',
  success: 'done',
  ghost: 'gone',
  compacting: 'compacting',
  looping: 'looping',
  typing: 'your draft',
}

export function PixelBadge({ status, label, style }: PixelBadgeProps) {
  const text = label ?? labelByStatus[status] ?? status
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        flexShrink: 0,
        gap: 6,
        padding: '2px 8px 0',
        background: 'var(--corp-cream-100)',
        boxShadow: `inset 0 0 0 1px ${colorByStatus[status]}`,
        fontFamily: 'var(--corp-font-ui)',
        fontSize: 'var(--corp-text-body-sm)',
        lineHeight: '18px',
        color: 'var(--corp-ink-900)',
        userSelect: 'none',
        ...style,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          background: colorByStatus[status],
          boxShadow: 'inset 0 0 0 1px var(--corp-ink-300)',
        }}
      />
      {text}
    </span>
  )
}
