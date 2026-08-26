// 16×16 pixel icons. 2 colors max. Integer paths only.
// Ported verbatim from the MIT-licensed reference design system (see
// /THIRD_PARTY_SKILLS.md) — token names adapted (--cth-* -> --corp-*),
// path data and component structure otherwise unchanged. Add to the
// library by extending `paths` below, in the same 16x16/crispEdges/
// currentColor style.

import type { CSSProperties } from 'react'

export type IconName =
  | 'gear'
  | 'plus'
  | 'x'
  | 'check'
  | 'arrow-right'
  | 'pause'
  | 'play'
  | 'bell'
  | 'folder'
  | 'terminal'
  | 'code'
  | 'web'
  | 'mcp'
  | 'sparkle'
  | 'expand'
  | 'minimize'
  | 'clock'
  | 'mic'
  | 'ledger'
  | 'info'
  | 'sidebar'
  | 'image'
  | 'edit'
  | 'git'
  // Additions for tabs/features this app has that the reference doesn't —
  // drawn in the same 16x16/hairline/evenodd style, not a different
  // icon language.
  | 'book'
  | 'share'
  | 'brain'
  | 'wrench'
  | 'zap'
  | 'list'
  | 'question'
  | 'activity'
  | 'monitor'
  | 'sun'
  | 'moon'
  | 'crown'
  | 'mail'
  | 'trash'
  | 'chevron-right'

interface IconDef {
  ink: string // primary color path d
  accent?: string // optional accent color path d
  accentColor: string // CSS var name
}

const paths: Record<IconName, IconDef> = {
  gear: {
    accentColor: 'var(--corp-ink-300)',
    ink: 'M6 1h4v3h2v2h3v4h-3v2h-2v3h-4v-3h-2v-2h-3v-4h3v-2h2v-3zM6 6h4v4h-4z',
  },
  plus: {
    accentColor: 'var(--corp-mint)',
    ink: 'M7 2h2v5h5v2H9v5H7V9H2V7h5V2z',
  },
  x: {
    accentColor: 'var(--corp-coral)',
    ink: 'M3 3h2v2h2v2h2V5h2V3h2v2h-2v2h-2v2h2v2h2v2h-2v-2h-2V9H7v2H5v2H3v-2h2v-2h2V7H5V5H3V3z',
  },
  check: {
    accentColor: 'var(--corp-mint)',
    ink: 'M13 4h2v2h-2v2h-2v2H9v2H7v2H5v-2H3v-2H1V8h2v2h2v2h2v-2h2V8h2V6h2V4z',
  },
  'arrow-right': {
    accentColor: 'var(--corp-sky)',
    ink: 'M8 3h2v2h2v2h2v2h-2v2h-2v2H8v-2h2V9H2V7h8V5H8V3z',
  },
  edit: {
    accentColor: 'var(--corp-lilac)',
    ink: 'M13 1h2v1h-2zM1 2h10v1h-10zM12 2h2v1h-2zM1 3h1v1h-1zM11 3h2v1h-2zM1 4h1v1h-1zM10 4h2v1h-2zM1 5h1v1h-1zM9 5h2v1h-2zM1 6h1v1h-1zM3 6h5v1h-5zM9 6h1v1h-1zM1 7h1v1h-1zM10 7h1v1h-1zM1 8h1v1h-1zM10 8h1v1h-1zM1 9h1v1h-1zM3 9h5v1h-5zM10 9h1v1h-1zM1 10h1v1h-1zM10 10h1v1h-1zM1 11h1v1h-1zM10 11h1v1h-1zM1 12h1v1h-1zM3 12h5v1h-5zM10 12h1v1h-1zM1 13h1v1h-1zM10 13h1v1h-1zM1 14h1v1h-1zM10 14h1v1h-1zM1 15h10v1h-10z',
  },
  pause: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M4 3h3v10H4V3zm5 0h3v10H9V3z',
  },
  play: {
    accentColor: 'var(--corp-mint)',
    ink: 'M4 3h2v2h2v2h2v2H8v2H6v2H4V3z',
  },
  bell: {
    accentColor: 'var(--corp-peach)',
    ink: 'M7 1h2v1h1v1h1v6h1v2H3V9h1V3h1V2h1V1h1zm0 12h2v2H7v-2z',
  },
  folder: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M1 3h6v1h8v9H1V3zm1 1v8h12V5H6V4H2z',
  },
  image: {
    accentColor: 'var(--corp-lemon)',
    accent: 'M4 5h2v2H4V5z',
    ink: 'M1 2h14v12H1V2zm1 1v10h12V3H2zM8 6h2v1H8zM7 7h4v1H7zM6 8h6v1H6zM5 9h8v1H5zM4 10h9v2H4z',
  },
  terminal: {
    accentColor: 'var(--corp-mint)',
    ink: 'M1 2h14v12H1V2zm1 1v10h12V3H2zm1 2h1v1h1v1h1v1H5v1H4v1H3V9h1V8h1V7H4V6H3V5zm5 5h4v1H8v-1z',
  },
  git: {
    accentColor: 'var(--corp-coral)',
    ink: 'M5 1h3v1h-3zM4 2h1v1h-1zM8 2h1v1h-1zM4 3h1v1h-1zM8 3h1v1h-1zM5 4h3v1h-3zM6 5h1v1h-1zM6 6h1v1h-1zM9 6h3v1h-3zM6 7h1v1h-1zM8 7h1v1h-1zM12 7h1v1h-1zM6 8h3v1h-3zM12 8h1v1h-1zM6 9h1v1h-1zM9 9h3v1h-3zM6 10h1v1h-1zM5 11h3v1h-3zM4 12h1v1h-1zM8 12h1v1h-1zM4 13h1v1h-1zM8 13h1v1h-1zM5 14h3v1h-3z',
  },
  code: {
    accentColor: 'var(--corp-sky)',
    ink: 'M5 3h1v1H5v1H4v1H3v1H2v1h1v1h1v1h1v1h1v1H5v-1H4v-1H3v-1H2v-1H1V7h1V6h1V5h1V4h1V3zm5 0h1v1h1v1h1v1h1v1h1v1h-1v1h-1v1h-1v1h-1v1h-1v-1h1v-1h1v-1h1V9h1V7h-1V6h-1V5h-1V4h-1V3z',
  },
  web: {
    accentColor: 'var(--corp-lilac)',
    ink: 'M7 1h2v1h2v1h1v1h1v2h1v2h-1v2h-1v1h-1v1H9v1H7v-1H5v-1H4v-1H3V9H2V7h1V5h1V4h1V3h2V2h0V1zm0 2v1H5v1H4v1H3v2h2V8h0V7h2V6h0V5h2V4h0V3H7zm2 1h1v1h1v1h1v2h-1v1H9V8h1V7h0V6h0V5h-1V4z',
  },
  mcp: {
    accentColor: 'var(--corp-lilac)',
    ink: 'M8 1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h-1v1h-1v1h-1v1h-1v1h-1v1H8v1H7v-1H6v-1H5v-1H4v-1H3v-1H2V9H1V8h1V7h1V6h1V5h1V4h1V3h1V2h1V1zm0 2v1H7v1H6v1H5v1H4v1H3v1h1v1h1v1h1v1h1v1h1v1h1v-1h1v-1h1v-1h1v-1h1V9h1V8h-1V7h-1V6h-1V5h-1V4h-1V3h-1V2H8z',
  },
  sparkle: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M8 1h1v3h3v1H9v3H8V5H5V4h3V1zm-4 8h1v2h2v1H5v2H4v-2H2v-1h2V9zm8-1h1v2h2v1h-2v2h-1v-2H10v-1h2V8z',
  },
  expand: {
    accentColor: 'var(--corp-sky)',
    ink: 'M1 1h6v2H3v4H1V1zm14 0v6h-2V3H9V1h6zM1 9h2v4h4v2H1V9zm14 0v6H9v-2h4V9h2z',
  },
  minimize: {
    accentColor: 'var(--corp-sky)',
    ink: 'M5 1h2v6H1V5h4V1zm4 0h2v4h4v2H9V1zM1 9h6v6H5v-4H1V9zm8 0h6v2h-4v4H9V9z',
  },
  clock: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M5 1h6v1h2v2h1v2h1v4h-1v2h-1v2h-2v1H5v-1H3v-2H2V8H1V6h1V4h1V2h2V1zm0 2H4v1H3v2H2v4h1v2h1v1h1v1h6v-1h1v-1h1v-2h1V6h-1V4h-1V3h-1V2H5v1zm2 1h2v4h2v1h1v1h-1v1h-1v-1H9v1H7V4z',
  },
  ledger: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M2 1h12v14H2V1zM3 2v12h10V2H3zM5 4h6v1H5zM5 7h6v1H5zM5 10h4v1H5z',
  },
  mic: {
    accentColor: 'var(--corp-coral)',
    ink: 'M6 2h4v7H6V2z M4 9h1v2H4z M11 9h1v2h-1z M4 11h8v1H4z M7 12h2v2H7z M5 14h6v1H5z',
  },
  info: {
    accentColor: 'var(--corp-sky)',
    ink: 'M5 1h6v1h2v1h1v2h1v6h-1v2h-1v1h-2v1H5v-1H3v-1H2v-2H1V5h1V3h1V2h2V1z M7 4h2v2H7z M7 7h2v5H7z',
  },
  sidebar: {
    accentColor: 'var(--corp-ink-300)',
    ink: 'M1 3h14v10H1z M2 4h12v8H2z M2 4h4v8H2z',
  },
  // --- additions for our own tabs, same style/weight as the set above ---
  book: {
    accentColor: 'var(--corp-lilac)',
    ink: 'M2 2h5v12H2zM9 2h5v12H9zM3 3v10h3V3zM10 3v10h3V3zM4 5h1v1H4zM11 5h1v1h-1z',
  },
  share: {
    accentColor: 'var(--corp-sky)',
    ink: 'M11 1h4v4h-2V3.4L7.4 9 6 7.6 11.6 2H11zM2 3h5v2H4v7h7v-3h2v5H2z',
  },
  brain: {
    accentColor: 'var(--corp-lilac)',
    ink: 'M5 1h3v1h1v1h1v1h1v2h1v3h-1v2h-1v1h-1v1H8v1H5v-1H4v-1H3v-1H2V9H1V6h1V4h1V2h1V1zm1 2v1H5v1H4v2H3v2h1v2h1v1h1v1h2v-1h1v-1h1V9h1V7h-1V5h-1V4h-1V3H6z',
  },
  wrench: {
    accentColor: 'var(--corp-peach)',
    ink: 'M10 1h1v1h1v1h1v1h1v1h-1v1h-1v1l3 3-2 2-3-3h-1v1h-1v-1H8v-1H7l-4 4-2-2 4-4V9H4V8H3V7h1V6h1V5h1v1h1v1h1V6H7V5H6V4h1V3h1V2h1V1z',
  },
  zap: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M9 1h2L9 7h4L6 15l1-6H4z',
  },
  list: {
    accentColor: 'var(--corp-mint)',
    ink: 'M2 3h2v2H2zM5 3h9v2H5zM2 7h2v2H2zM5 7h9v2H5zM2 11h2v2H2zM5 11h9v2H5z',
  },
  question: {
    accentColor: 'var(--corp-sky)',
    ink: 'M5 1h6v1h2v1h1v3h-1v1h-1v1H9v2H7V9h1V8h1V7h1V4H5V2h0V1zM7 11h2v2H7z',
  },
  activity: {
    accentColor: 'var(--corp-coral)',
    ink: 'M1 8h3l2-6 3 12 2-6h4v1h-3l-2 6-3-12-2 6H1z',
  },
  monitor: {
    accentColor: 'var(--corp-sky)',
    ink: 'M1 2h14v9H9v2h3v1H4v-1h3v-2H1V2zm1 1v7h12V3H2z',
  },
  sun: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M7 1h2v2H7zM7 13h2v2H7zM1 7h2v2H1zM13 7h2v2h-2zM2.5 2.5h2v2h-2zM11.5 2.5h2v2h-2zM2.5 11.5h2v2h-2zM11.5 11.5h2v2h-2zM5 5h6v6H5z',
  },
  moon: {
    accentColor: 'var(--corp-lilac)',
    ink: 'M9 1h2v1h1v1h1v2h1v4h-1v2h-1v1h-1v1H9v1H7v-1H6v-1H9v-1h1v-1h1v-1h1V6h-1V5h-1V4H9V3H7V2h2z',
  },
  crown: {
    accentColor: 'var(--corp-lemon)',
    ink: 'M2 5h2v1h1V4h1v2h2V4h1v2h2V4h1v2h1V5h2v6H2V5zm0 7h12v2H2z',
  },
  mail: {
    accentColor: 'var(--corp-sky)',
    ink: 'M1 3h14v10H1V3zm1 1v1l6 4 6-4V4zm0 3v5h12V7l-6 4z',
  },
  trash: {
    accentColor: 'var(--corp-coral)',
    ink: 'M6 1h4v1h4v2H2V2h4V1zM3 5h10v10H3V5zm2 2v6h1V7zm3 0v6h1V7zm3 0v6h1V7z',
  },
  'chevron-right': {
    accentColor: 'var(--corp-ink-300)',
    ink: 'M5 2h2v2h2v2h2v2H9v2H7v2H5v-2h2V9H5V7h2V5H5z',
  },
}

export interface IconProps {
  name: IconName
  size?: number // integer scale: 1 = 16px, 2 = 32px, ...
  style?: CSSProperties
}

export function Icon({ name, size = 1, style }: IconProps) {
  const def = paths[name]
  const dim = 16 * size
  return (
    <svg viewBox="0 0 16 16" width={dim} height={dim} shapeRendering="crispEdges" style={{ display: 'inline-block', ...style }} aria-hidden>
      {def.accent && <path d={def.accent} fill={def.accentColor} fillRule="evenodd" />}
      {/* currentColor, not a hardcoded --corp-ink-900: an icon is always the
          color of the text it sits beside, so it stays visible on an
          inverted surface (e.g. a primary PixelButton) instead of vanishing
          into a same-toned fill. */}
      <path d={def.ink} fill="currentColor" fillRule="evenodd" />
    </svg>
  )
}
