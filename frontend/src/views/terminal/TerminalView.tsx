import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { watchAgentTrace } from '../../lib/platformClient'

export function TerminalView({ orgId, agentId }: { orgId: string; agentId: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)

  useEffect(() => {
    let destroyed = false
    const term = new Terminal({
      convertEol: true,
      fontFamily: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
      fontSize: 13,
      theme: {
        background: '#1a1320', // --corp-ink-900
        foreground: '#d9cfe0', // --corp-ink-100
        cursor: '#dcab3c', // --corp-lemon
        selectionBackground: '#3d2e4a', // --corp-ink-700
        black: '#1a1320', red: '#d96a62', green: '#5ca97a', yellow: '#dcab3c',
        blue: '#6d87d6', magenta: '#9482d3', cyan: '#4f9faf', white: '#d9cfe0',
        brightBlack: '#6b5878', brightRed: '#e08c82', brightGreen: '#74c096',
        brightYellow: '#cfaa57', brightBlue: '#8095dc', brightMagenta: '#a896e3',
        brightCyan: '#6fb3c4', brightWhite: '#fffdf5',
      },
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)

    if (destroyed || !containerRef.current) {
      term.dispose()
    } else {
      term.open(containerRef.current)
      fitAddon.fit()
      termRef.current = term
    }

    return () => {
      destroyed = true
      termRef.current = null
      term.dispose()
    }
  }, [])

  useEffect(() => {
    return watchAgentTrace(orgId, agentId, (lines) => {
      const term = termRef.current
      if (!term) return
      term.clear()
      for (const line of lines) term.writeln(line)
    })
  }, [orgId, agentId])

  return (
    <div className="corp-panel" style={{ background: 'var(--corp-ink-900)', padding: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', color: 'var(--corp-ink-100)', fontFamily: 'var(--corp-font-mono)', fontSize: 'var(--corp-text-mono-sm)' }}>
        <span className="corp-status-dot corp-status-dot--live" style={{ background: 'var(--corp-mint)' }} />
        live
      </div>
      <div ref={containerRef} style={{ height: 320 }} />
    </div>
  )
}
