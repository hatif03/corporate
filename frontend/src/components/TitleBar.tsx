// Adapted from the reference design system's title bar, see
// /THIRD_PARTY_SKILLS.md — 36px height, cream gradient, bottom hairline,
// and the right-aligned icon-button cluster are ported as-is. The
// Electron-only drag region and macOS traffic-light clearance are dropped
// (no OS window chrome to clear on the web) — the one deliberate
// Electron->web adaptation.

import type { User } from 'firebase/auth'
import { Icon } from './Icon'
import { VoicePanel } from './VoicePanel'
import { useAppTheme, toggleAppTheme } from '../lib/theme'

function UserAvatar({ user }: { user: User }) {
  if (user.photoURL) {
    return <img src={user.photoURL} referrerPolicy="no-referrer" alt="" style={{ width: 24, height: 24, boxShadow: 'var(--corp-border-panel)' }} />
  }
  const initial = (user.email ?? '?').charAt(0).toUpperCase()
  return (
    <span
      className="corp-badge"
      style={{ width: 24, height: 24, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'var(--corp-sky-light)' }}
    >
      {initial}
    </span>
  )
}

const iconButtonStyle = {
  width: 28,
  height: 28,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--corp-paper-100)',
  boxShadow: 'inset 0 0 0 1px var(--corp-ink-300)',
  border: 'none',
  cursor: 'pointer',
  color: 'var(--corp-ink-900)',
} as const

export function TitleBar({ orgId, user, onOpenSettings, onSignOut }: { orgId: string; user: User; onOpenSettings: () => void; onSignOut: () => void }) {
  const theme = useAppTheme()

  return (
    <div
      style={{
        height: 36,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--corp-space-3)',
        padding: '0 var(--corp-space-3)',
        background: 'linear-gradient(180deg, var(--corp-cream-100) 0%, var(--corp-cream-200) 100%)',
        borderBottom: '1px solid var(--corp-ink-300)',
      }}
    >
      <span style={{ fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-sm)', lineHeight: 'var(--corp-lh-display-sm)' }}>Corporate</span>
      <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>
        org: {orgId}
      </span>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 'var(--corp-space-2)' }}>
        <VoicePanel orgId={orgId} />
        <button className="corp-tip" data-tip={theme === 'dark' ? 'Switch to light' : 'Switch to dark'} style={iconButtonStyle} onClick={() => toggleAppTheme()}>
          <Icon name={theme === 'dark' ? 'moon' : 'sun'} />
        </button>
        <button className="corp-tip" data-tip="Settings" style={iconButtonStyle} onClick={onOpenSettings}>
          <Icon name="gear" />
        </button>
        <UserAvatar user={user} />
        <span className="corp-text-muted" style={{ fontSize: 'var(--corp-text-body-sm)' }}>
          {user.email}
        </span>
        <button className="corp-tip" data-tip="Sign out" style={iconButtonStyle} onClick={onSignOut}>
          <Icon name="x" />
        </button>
      </div>
    </div>
  )
}
