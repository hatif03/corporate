// Modal shell adapted from the reference design system's SettingsModal
// pattern (backdrop + PixelPanel dialog variant, see /THIRD_PARTY_SKILLS.md)
// — the reference's own settings content (AI-engine picker, MCP defaults,
// voice device settings) doesn't apply here (see the plan's "what's not
// copied" list), so this wraps Corporate's own SettingsView content instead
// of porting their 6-tab surface verbatim.

import { Icon } from './Icon'
import { PixelButton } from './PixelButton'
import { PixelPanel } from './PixelPanel'
import { SettingsView } from '../views/settings/SettingsView'
import type { Agent } from '../lib/types'

export function SettingsModal({ orgId, agents, onClose }: { orgId: string; agents: Agent[]; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(26, 19, 32, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
      }}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(720px, 92vw)', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        <PixelPanel variant="dialog" style={{ maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--corp-space-3)', flexShrink: 0 }}>
            <h2 style={{ margin: 0, fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-md)', lineHeight: 'var(--corp-lh-display-md)' }}>
              Settings
            </h2>
            <PixelButton variant="ghost" size="sm" onClick={onClose} title="Close">
              <Icon name="x" />
            </PixelButton>
          </div>
          <div style={{ overflowY: 'auto', minHeight: 0 }}>
            <SettingsView orgId={orgId} agents={agents} />
          </div>
        </PixelPanel>
      </div>
    </div>
  )
}
