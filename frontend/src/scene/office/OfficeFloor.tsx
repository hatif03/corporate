import { useEffect, useRef } from 'react'
import { Application, Assets, Container, Graphics, Sprite, Text, Texture, TilingSprite } from 'pixi.js'
import { DEPARTMENT_ZONES, type DepartmentZone } from './departments'
import { CHARACTER_VARIANTS, DESK_TILE, FLOOR_TILE, variantForDepartment } from './tileset'
import { deskAnchorFor, getTargetPosition } from './movement'
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

const MOVE_SPEED = 1.6 // px/frame at 60fps
const WALK_FRAME_TICKS = 12 // how often to alternate walk-pose while moving

interface AgentSprite {
  container: Container
  charSprite: Sprite
  statusDot: Graphics
  target: { x: number; y: number }
  departmentId: string
  walkFrame: 0 | 1
  tickCount: number
}

/**
 * Real tile/sprite office floor (Kenney CC0 RPG Urban Pack, see tileset.ts):
 * a TilingSprite floor + a desk per department zone, and one character
 * sprite per agent that walks between a "desk" and "idle" anchor as its
 * status changes (movement.ts — pure client-side, see ADR-0013). Agents are
 * diffed against the previous frame instead of being torn down and rebuilt
 * on every Firestore tick, so an in-progress walk is never interrupted.
 */
export function OfficeFloor({ agents }: { agents: Agent[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<Application | null>(null)
  const readyRef = useRef(false)
  const spritesRef = useRef<Map<string, AgentSprite>>(new Map())
  const texturesRef = useRef<Map<string, Texture>>(new Map())
  const agentsRef = useRef<Agent[]>(agents)
  agentsRef.current = agents

  function reconcile(currentAgents: Agent[]) {
    const app = appRef.current
    const textures = texturesRef.current
    if (!app || !readyRef.current) return

    const seen = new Set<string>()
    // Stable per-zone ordering: same input always produces the same
    // anchor assignment on every client, with no coordination needed.
    const sortedByZone = new Map<string, Agent[]>()
    for (const a of [...currentAgents].sort((x, y) => x.id.localeCompare(y.id))) {
      const list = sortedByZone.get(a.department) ?? []
      list.push(a)
      sortedByZone.set(a.department, list)
    }

    for (const zone of DEPARTMENT_ZONES) {
      const zoneAgents = sortedByZone.get(zone.id) ?? []
      zoneAgents.forEach((agent, indexInZone) => {
        seen.add(agent.id)
        const target = getTargetPosition(agent, zone, indexInZone)
        let sprite = spritesRef.current.get(agent.id)

        if (!sprite) {
          const variant = variantForDepartment(agent.department)
          const container = new Container()
          container.position.set(target.x, target.y)

          const charSprite = new Sprite(textures.get(variant.idle))
          charSprite.anchor.set(0.5, 0.9)
          charSprite.scale.set(1.4)
          container.addChild(charSprite)

          const statusDot = new Graphics()
          container.addChild(statusDot)

          app.stage.addChild(container)
          sprite = { container, charSprite, statusDot, target, departmentId: agent.department, walkFrame: 0, tickCount: 0 }
          spritesRef.current.set(agent.id, sprite)
        }

        sprite.target = target
        sprite.departmentId = agent.department
        const variant = variantForDepartment(agent.department)
        sprite.statusDot.clear().circle(10, -4, 5).fill({ color: STATUS_DOT_COLOR[agent.status] ?? 0xa899b5 }).stroke({
          width: 1,
          color: 0x2b2b2b,
        })
        // Idle texture swap only needs to happen when not mid-walk-animation
        // — the ticker owns texture swaps while actually moving.
        const dist = Math.hypot(target.x - sprite.container.x, target.y - sprite.container.y)
        if (dist <= 0.5) sprite.charSprite.texture = textures.get(variant.idle) ?? sprite.charSprite.texture
      })
    }

    for (const [id, sprite] of spritesRef.current) {
      if (!seen.has(id)) {
        sprite.container.destroy({ children: true })
        spritesRef.current.delete(id)
      }
    }
  }

  useEffect(() => {
    let destroyed = false
    const app = new Application()
    appRef.current = app

    async function setup() {
      await app.init({ width: 540, height: 340, backgroundColor: 0xf4f1ea, antialias: true })
      if (destroyed || !containerRef.current) {
        app.destroy(true)
        return
      }
      containerRef.current.appendChild(app.canvas)

      const allSprites = [
        FLOOR_TILE,
        DESK_TILE,
        ...CHARACTER_VARIANTS.flatMap((v) => [v.idle, v.walkA, v.walkB]),
      ]
      const loaded = (await Assets.load(allSprites)) as Record<string, Texture>
      for (const [url, texture] of Object.entries(loaded)) texturesRef.current.set(url, texture)
      if (destroyed) return

      for (const zone of DEPARTMENT_ZONES) {
        const floor = new TilingSprite({
          texture: texturesRef.current.get(FLOOR_TILE),
          width: zone.width,
          height: zone.height,
        })
        floor.position.set(zone.x, zone.y)
        floor.tint = zone.color
        floor.alpha = 0.55
        app.stage.addChild(floor)

        const border = new Graphics().rect(zone.x, zone.y, zone.width, zone.height).stroke({ width: 2, color: 0x2b2b2b })
        app.stage.addChild(border)

        const label = new Text({
          text: zone.displayName,
          style: { fontSize: 12, fill: 0x1c1c1c, fontWeight: 'bold' },
        })
        label.position.set(zone.x + 6, zone.y + 4)
        app.stage.addChild(label)

        const desk = new Sprite(texturesRef.current.get(DESK_TILE))
        desk.anchor.set(0.5)
        desk.scale.set(1.6)
        const deskAnchor = deskAnchorFor(zone as DepartmentZone)
        desk.position.set(deskAnchor.x, deskAnchor.y + 10)
        app.stage.addChild(desk)
      }

      app.ticker.add(() => {
        for (const sprite of spritesRef.current.values()) {
          const dx = sprite.target.x - sprite.container.x
          const dy = sprite.target.y - sprite.container.y
          const dist = Math.hypot(dx, dy)

          if (dist > 0.5) {
            const step = Math.min(MOVE_SPEED, dist)
            sprite.container.x += (dx / dist) * step
            sprite.container.y += (dy / dist) * step
            if (dx !== 0) sprite.charSprite.scale.x = (dx < 0 ? -1 : 1) * Math.abs(sprite.charSprite.scale.x)

            sprite.tickCount += 1
            if (sprite.tickCount >= WALK_FRAME_TICKS) {
              sprite.tickCount = 0
              sprite.walkFrame = sprite.walkFrame === 0 ? 1 : 0
              const variant = variantForDepartment(sprite.departmentId)
              const walkTexture = sprite.walkFrame === 0 ? variant.walkA : variant.walkB
              sprite.charSprite.texture = texturesRef.current.get(walkTexture) ?? sprite.charSprite.texture
            }
          }
        }
      })

      readyRef.current = true
      reconcile(agentsRef.current)
    }

    void setup()

    return () => {
      destroyed = true
      readyRef.current = false
      spritesRef.current.clear()
      app.destroy(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    reconcile(agents)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents])

  return <div ref={containerRef} className="corp-panel" style={{ width: 'fit-content' }} />
}
