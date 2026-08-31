// Pre-auth landing page, replacing the old bare SignInGate. Structure
// (hero -> how-it-works -> live-office teaser -> capabilities -> footer)
// is adapted from https://munderdiffl.in/'s layout — but not its content:
// that's a downloadable local CLI harness with paid tiers and a download
// picker, none of which applies to this hosted web app. Copy below comes
// from this project's own README/settings copy, not invented.

import { Icon, type IconName } from '../../components/Icon'
import { PixelButton } from '../../components/PixelButton'
import { PixelPanel } from '../../components/PixelPanel'
import { OfficeFloor } from '../../scene/office/OfficeFloor'
import { CAPABILITIES } from '../settings/SettingsView'
import { signInWithGoogle } from '../../lib/authClient'

const HOW_IT_WORKS: { icon: IconName; title: string; body: string }[] = [
  { icon: 'mail', title: 'Dispatch a goal', body: 'Tell the CEO agent what you need, in plain language, from the Command Center or a webhook/schedule trigger.' },
  { icon: 'share', title: 'The CEO delegates', body: 'It breaks the goal into real tasks and routes them to the right department agents over the message bus — no manual assignment.' },
  { icon: 'monitor', title: 'Watch it happen live', body: 'See every agent think, message, and finish work in real time on the office floor and in the Command Center tabs.' },
]

const DEPARTMENTS = [
  'Finance & Audit',
  'Engineering & SRE',
  'Legal & Risk',
  'Office of the CEO',
  'Sales & CRM',
  'HR & People Ops',
  'Customer Support',
  'Marketing & Comms',
  'Product & Data Analytics',
]

export function LandingPage() {
  return (
    <div style={{ minHeight: '100vh', padding: 'var(--corp-space-5) var(--corp-space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--corp-space-6)', maxWidth: 1100, margin: '0 auto' }}>
      <section style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 'var(--corp-space-4)', paddingTop: 'var(--corp-space-5)' }}>
        <h1
          style={{
            margin: 0,
            fontFamily: 'var(--corp-font-display)',
            fontSize: 'var(--corp-text-display-lg)',
            lineHeight: 'var(--corp-lh-display-lg)',
            letterSpacing: '0.04em',
          }}
        >
          Corporate
        </h1>
        <p className="corp-text-muted" style={{ margin: 0, maxWidth: 560, fontSize: 'var(--corp-text-body-md)' }}>
          A virtual company: a 2D pixel-art office floor where autonomous AI employees work across real
          departments — Finance, Engineering, Legal, and more — coordinated by a CEO agent, all visible and
          controllable through a Command Center dashboard.
        </p>
        <PixelButton variant="primary" size="lg" onClick={() => signInWithGoogle()}>
          Sign in with Google
        </PixelButton>

        <PixelPanel variant="inset" noPadding style={{ width: '100%', maxWidth: 640, aspectRatio: '16 / 9', overflow: 'hidden' }}>
          <video
            controls
            playsInline
            style={{ width: '100%', height: '100%', display: 'block', objectFit: 'cover' }}
            src="/media/corporate-demo.mp4"
          />
        </PixelPanel>
      </section>

      <section>
        <h2 style={{ textAlign: 'center', fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-md)' }}>How it works</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--corp-space-4)' }}>
          {HOW_IT_WORKS.map((step, i) => (
            <PixelPanel key={step.title}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span className="corp-badge" style={{ background: 'var(--corp-sky-light)' }}>{i + 1}</span>
                <Icon name={step.icon} />
                <strong>{step.title}</strong>
              </div>
              <p className="corp-text-muted" style={{ margin: 0, fontSize: 'var(--corp-text-body-sm)' }}>{step.body}</p>
            </PixelPanel>
          ))}
        </div>
      </section>

      <section>
        <h2 style={{ textAlign: 'center', fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-md)' }}>The office floor</h2>
        <PixelPanel variant="terminal" noPadding style={{ height: 360, overflow: 'hidden' }}>
          <OfficeFloor agents={[]} orgId="demo" />
        </PixelPanel>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center', marginTop: 10 }}>
          {DEPARTMENTS.map((d) => (
            <span key={d} className="corp-badge" style={{ background: 'var(--corp-lilac)' }}>{d}</span>
          ))}
        </div>
      </section>

      <section>
        <h2 style={{ textAlign: 'center', fontFamily: 'var(--corp-font-display)', fontSize: 'var(--corp-text-display-md)' }}>What this company can do</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
          {CAPABILITIES.map((c) => (
            <div key={c.name} className="corp-panel" style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <Icon name={c.icon} style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <strong>{c.name}</strong>
                <div className="corp-text-muted" style={{ fontSize: '0.8rem' }}>{c.description}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="corp-text-muted" style={{ textAlign: 'center', fontSize: 'var(--corp-text-body-sm)', padding: 'var(--corp-space-4) 0' }}>
        Built for the All Things Agentic hackathon — track: The Fortified Enterprise Fleet.
      </footer>
    </div>
  )
}
