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
    const term = new Terminal({ convertEol: true, theme: { background: '#1c1c1c' } })
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
    <div className="corp-panel" style={{ background: '#1c1c1c', padding: 4 }}>
      <div ref={containerRef} style={{ height: 320 }} />
    </div>
  )
}
