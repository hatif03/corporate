// App-wide light/dark theme — one switch for the whole UI via a single
// `data-theme` token swap (see design/tokens.css's dark override block).
// Ported from the MIT-licensed reference design system, see
// /THIRD_PARTY_SKILLS.md. Subscribable module (not React state) so any
// component can read it with useAppTheme() without prop-drilling; the one
// toggle button lives in TitleBar.

import { useSyncExternalStore } from 'react'

export type AppTheme = 'light' | 'dark'

const LS_KEY = 'corp.theme'

function load(): AppTheme {
  try {
    const v = window.localStorage.getItem(LS_KEY)
    if (v === 'dark' || v === 'light') return v
  } catch {
    /* noop */
  }
  return 'light'
}

let theme: AppTheme = load()
const subscribers = new Set<() => void>()

function apply(): void {
  try {
    document.documentElement.dataset.theme = theme
  } catch {
    /* SSR/tests */
  }
}
apply()

export function appTheme(): AppTheme {
  return theme
}

export function setAppTheme(next: AppTheme): void {
  if (next === theme) return
  theme = next
  try {
    window.localStorage.setItem(LS_KEY, next)
  } catch {
    /* noop */
  }
  apply()
  subscribers.forEach((fn) => fn())
}

export function toggleAppTheme(): AppTheme {
  const next: AppTheme = theme === 'dark' ? 'light' : 'dark'
  setAppTheme(next)
  return next
}

export function useAppTheme(): AppTheme {
  return useSyncExternalStore(
    (onChange) => {
      subscribers.add(onChange)
      return () => subscribers.delete(onChange)
    },
    () => theme,
  )
}
