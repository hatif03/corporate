// Ported from the MIT-licensed reference design system, see
// /THIRD_PARTY_SKILLS.md. Token names adapted (--cth-panel-border* ->
// --corp-border-*, --cth-* -> --corp-*), otherwise verbatim.

import type { CSSProperties, ReactNode } from 'react'

export type AccentColorName = 'coral' | 'mint' | 'sky' | 'lemon' | 'lilac' | 'peach'

type Variant = 'default' | 'inset' | 'active' | 'terminal' | 'dialog'

export interface PixelPanelProps {
  variant?: Variant
  title?: string
  accent?: AccentColorName
  children?: ReactNode
  style?: CSSProperties
  className?: string
  noPadding?: boolean
}

const borderByVariant: Record<Variant, string> = {
  default: 'var(--corp-border-panel)',
  inset: 'var(--corp-border-panel-inset)',
  active: 'var(--corp-border-panel)', // accent overlay added separately
  terminal: 'var(--corp-border-terminal)',
  dialog: 'var(--corp-border-dialog)',
}

const fillByVariant: Record<Variant, string> = {
  default: 'var(--corp-cream-100)',
  inset: 'var(--corp-cream-200)',
  active: 'var(--corp-cream-100)',
  terminal: 'var(--corp-paper-100)',
  dialog: 'var(--corp-cream-50)',
}

export function PixelPanel({ variant = 'default', title, accent, children, style, className, noPadding = false }: PixelPanelProps) {
  const baseStyle: CSSProperties = {
    background: fillByVariant[variant],
    boxShadow: borderByVariant[variant],
    padding: noPadding ? 0 : 'var(--corp-space-3)',
    position: 'relative',
    ...style,
  }

  // Active variant: paint the accent over the middle border slot (3px ring
  // at 1px inset) — used for selection/focus-style accent framing.
  if (variant === 'active' && accent) {
    baseStyle.boxShadow = `
      inset 0 0 0 1px var(--corp-ink-100),
      inset 0 0 0 3px var(--corp-${accent}),
      inset 0 0 0 5px var(--corp-ink-900)`
  }

  return (
    <div className={className} style={baseStyle}>
      {title && (
        <div
          style={{
            margin: noPadding ? 0 : '-12px -12px 12px',
            padding: '6px 12px 4px',
            background: accent ? `var(--corp-${accent})` : 'var(--corp-cream-200)',
            color: 'var(--corp-ink-900)',
            fontFamily: 'var(--corp-font-display)',
            fontSize: 'var(--corp-text-display-md)',
            lineHeight: 'var(--corp-lh-display-md)',
            boxShadow: 'inset 0 -1px 0 var(--corp-ink-900)',
          }}
        >
          {title}
        </div>
      )}
      {children}
    </div>
  )
}
