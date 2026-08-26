// Ported from the MIT-licensed reference design system, see
// /THIRD_PARTY_SKILLS.md. Token names adapted (--cth-*  -> --corp-*),
// otherwise verbatim.

import { type CSSProperties, type ReactNode, useState } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'destructive'
type Size = 'sm' | 'md' | 'lg'

export interface PixelButtonProps {
  variant?: Variant
  size?: Size
  children?: ReactNode
  onClick?: () => void
  disabled?: boolean
  fullWidth?: boolean
  style?: CSSProperties
  title?: string
}

const heightBySize: Record<Size, number> = { sm: 24, md: 32, lg: 40 }
const padBySize: Record<Size, string> = { sm: '0 8px', md: '0 12px', lg: '0 16px' }

export function PixelButton({
  variant = 'primary',
  size = 'md',
  children,
  onClick,
  disabled = false,
  fullWidth = false,
  style,
  title,
}: PixelButtonProps) {
  const [pressed, setPressed] = useState(false)
  const [hover, setHover] = useState(false)

  // Disabled text is its own color, not the variant's — every variant swaps
  // its fill to cream-300 when disabled, but primary's enabled text
  // (cream-50, picked to sit on an ink-900 fill) collapses to near-invisible
  // against cream-300 in both themes. ink-500 is the one foreground that
  // reads against cream-300 in both themes, and a muted label is what a
  // disabled control should look like anyway.
  const disabledText = 'var(--corp-ink-500)'

  const palette = (() => {
    switch (variant) {
      case 'primary':
        return {
          fill: disabled ? 'var(--corp-cream-300)' : hover ? 'var(--corp-ink-700)' : 'var(--corp-ink-900)',
          text: disabled ? disabledText : 'var(--corp-cream-50)',
          border: 'var(--corp-ink-900)',
          shadow: 'var(--corp-ink-900)',
        }
      case 'secondary':
        return {
          fill: disabled ? 'var(--corp-cream-300)' : hover ? 'var(--corp-cream-200)' : 'var(--corp-cream-100)',
          text: disabled ? disabledText : 'var(--corp-ink-900)',
          border: 'var(--corp-ink-300)',
          shadow: 'var(--corp-ink-100)',
        }
      case 'ghost':
        return {
          fill: hover ? 'var(--corp-cream-200)' : 'transparent',
          text: disabled ? disabledText : 'var(--corp-ink-700)',
          border: 'var(--corp-ink-300)',
          shadow: 'var(--corp-ink-100)',
        }
      case 'destructive':
        return {
          fill: disabled ? 'var(--corp-cream-300)' : hover ? 'var(--corp-coral-light)' : 'var(--corp-coral)',
          text: disabled ? disabledText : 'var(--corp-ink-900)',
          border: 'var(--corp-ink-500)',
          shadow: 'var(--corp-ink-300)',
        }
    }
  })()

  return (
    <button
      title={title}
      onClick={disabled ? undefined : onClick}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => {
        setPressed(false)
        setHover(false)
      }}
      onMouseEnter={() => setHover(true)}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
        lineHeight: 1,
        flexShrink: 0,
        height: heightBySize[size],
        padding: padBySize[size],
        background: palette.fill,
        color: palette.text,
        border: 'none',
        // 1px hairline + 1px lift — a 2px offset reads as a heavier box.
        boxShadow: pressed && !disabled ? `inset 0 0 0 1px ${palette.border}` : `inset 0 0 0 1px ${palette.border}, 0 1px 0 ${palette.shadow}`,
        transform: pressed && !disabled ? 'translateY(1px)' : 'none',
        fontFamily: 'var(--corp-font-ui)',
        fontSize: size === 'lg' ? 'var(--corp-text-body-md)' : 'var(--corp-text-body-sm)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        width: fullWidth ? '100%' : 'auto',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      {children}
    </button>
  )
}
