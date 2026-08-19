import { useEffect, useRef } from 'react'
import { Application, Graphics, Text } from 'pixi.js'
import { DEPARTMENT_ZONES } from './departments'
import type { Agent } from '../../lib/types'

const STATUS_DOT_COLOR: Record<string, number> = {
  idle: 0xa899b5,
  thinking: 0x4ecdc4,
  working: 0xffd93d,
  waiting: 0x6c8ef5,
  blocked: 0xff6b6b,
  success: 0x6bcf7f,
  ghost: 0xd9cfe0,
  compacting: 0x9b7ede,
  looping: 0xff9f43,
  typing: 0xffd93d,
}

/**
 * A placeholder office floor: department zones as flat-colored rectangles
 * with a status-colored dot per agent currently in that department. This is
 * the asset swap-point noted in docs/system_prompt.md — replace the
 * Graphics-drawn rectangles/dots with real sprite sheets (character walk
 * cycles, desk/tile art) without touching the zone-layout data in
 * departments.ts or the status-color mapping here.
 */
export function OfficeFloor({ agents }: { agents: Agent[] }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let destroyed = false
    const app = new Application()

    async function setup() {
      await app.init({ width: 500, height: 360, backgroundColor: 0xf4f1ea, antialias: true })
      if (destroyed || !containerRef.current) {
        app.destroy(true);
        return
      }
      containerRef.current.appendChild(app.canvas)

      for (const zone of DEPARTMENT_ZONES) {
        const rect = new Graphics()
          .rect(zone.x, zone.y, zone.width, zone.height)
          .fill({ color: zone.color, alpha: 0.35 })
          .stroke({ width: 2, color: 0x2b2b2b })
        app.stage.addChild(rect)

        const label = new Text({
          text: zone.displayName,
          style: { fontSize: 12, fill: 0x1c1c1c, fontWeight: 'bold' },
        })
        label.position.set(zone.x + 6, zone.y + 4)
        app.stage.addChild(label)

        const inZone = agents.filter((a) => a.department === zone.id)
        inZone.forEach((agent, i) => {
          const dot = new Graphics()
            .circle(0, 0, 8)
            .fill({ color: STATUS_DOT_COLOR[agent.status] ?? 0xa899b5 })
            .stroke({ width: 1, color: 0x2b2b2b })
          dot.position.set(zone.x + 20 + i * 24, zone.y + zone.height - 20)
          app.stage.addChild(dot)
        })
      }
    }

    void setup()

    return () => {
      destroyed = true
      app.destroy(true)
    }
  }, [agents])

  return <div ref={containerRef} className="corp-panel" style={{ width: 'fit-content' }} />
}
