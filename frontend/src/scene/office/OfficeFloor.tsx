import { useEffect, useRef } from 'react'
import { Application, Assets, Container, Graphics, Sprite, Text, Texture, TilingSprite } from 'pixi.js'
import { DEPARTMENT_ZONES, type DepartmentZone } from './departments'
import { ART_TILE, CABINET_TILE, CHARACTER_VARIANTS, DESK_TILE, FLOOR_TILE, PLANT_TILE, TRASH_TILE, variantForDepartment } from './tileset'
import {
  artAnchorFor,
  cabinetAnchorFor,
  deskAnchorFor,
  getTargetPosition,
  hashId,
  plantAnchorFor,
  trashAnchorFor,
  wanderOffset,
} from './movement'
import type { Agent, AgentStatus } from '../../lib/types'

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

const ACTIVE_STATUSES: AgentStatus[] = ['thinking', 'working', 'typing', 'looping', 'compacting']

const MOVE_SPEED = 1.6 // px/frame at 60fps
const WALK_FRAME_TICKS = 12 // how often to alternate walk-pose while moving
const BOB_AMPLITUDE_IDLE = 1.2 // px — a subtle "breathing" bob so nobody ever looks frozen
const BOB_AMPLITUDE_ACTIVE = 2.2 // px — a slightly busier bob while actively working
const BOB_SPEED_IDLE = 0.05 // radians/frame
const BOB_SPEED_ACTIVE = 0.11 // radians/frame
const GLOW_SPEED = 0.06 // radians/frame — pulsing "at work" glow under active agents

interface AgentSprite {
  container: Container
  charSprite: Sprite
  statusDot: Graphics
  glow: Graphics
  baseTarget: { x: number; y: number }
  departmentId: string
  status: AgentStatus
  walkFrame: 0 | 1
  tickCount: number
  bobPhase: number
}

/**
 * Real tile/sprite office floor (Kenney CC0 RPG Urban Pack, see tileset.ts):
 * a TilingSprite floor + a small furniture set per department zone (desk,
 * cabinet, plant, trash, wall art), and one character sprite per agent that
 * walks between a "desk" and "idle" anchor as its status changes
 * (movement.ts — pure client-side, see ADR-0013). Agents are diffed against
 * the previous frame instead of being torn down and rebuilt on every
 * Firestore tick, so an in-progress walk is never interrupted.
 *
 * On top of that base: every agent sprite has a continuous subtle
 * "breathing" bob (never fully static), idle agents drift in a slow ambient
 * wander around their idle anchor instead of freezing at one point, active
 * agents get a pulsing glow at their desk, and the office plant sways —
 * meant to read as a living, working office rather than a static diagram.
 */
export function OfficeFloor({ agents }: { agents: Agent[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<Application | null>(null)
  const readyRef = useRef(false)
  const spritesRef = useRef<Map<string, AgentSprite>>(new Map())
  const texturesRef = useRef<Map<string, Texture>>(new Map())
  const plantsRef = useRef<Sprite[]>([])
  const tickRef = useRef(0)
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
        const baseTarget = getTargetPosition(agent, zone, indexInZone)
        let sprite = spritesRef.current.get(agent.id)

        if (!sprite) {
          const variant = variantForDepartment(agent.department)
          const container = new Container()
          container.position.set(baseTarget.x, baseTarget.y)

          const glow = new Graphics()
          container.addChild(glow)

          const charSprite = new Sprite(textures.get(variant.idle))
          charSprite.anchor.set(0.5, 0.9)
          charSprite.scale.set(1.4)
          container.addChild(charSprite)

          const statusDot = new Graphics()
          container.addChild(statusDot)

          app.stage.addChild(container)
          sprite = {
            container,
            charSprite,
            statusDot,
            glow,
            baseTarget,
            departmentId: agent.department,
            status: agent.status,
            walkFrame: 0,
            tickCount: 0,
            bobPhase: (hashId(agent.id) % 1000) / 1000 * Math.PI * 2,
          }
          spritesRef.current.set(agent.id, sprite)
        }

        sprite.baseTarget = baseTarget
        sprite.departmentId = agent.department
        sprite.status = agent.status
        const variant = variantForDepartment(agent.department)
        sprite.statusDot.clear().circle(10, -4, 5).fill({ color: STATUS_DOT_COLOR[agent.status] ?? 0xa899b5 }).stroke({
          width: 1,
          color: 0x2b2b2b,
        })
        // Idle texture swap only needs to happen when not mid-walk-animation
        // — the ticker owns texture swaps while actually moving.
        const dist = Math.hypot(baseTarget.x - sprite.container.x, baseTarget.y - sprite.container.y)
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
        CABINET_TILE,
        PLANT_TILE,
        TRASH_TILE,
        ART_TILE,
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

        const cabinet = new Sprite(texturesRef.current.get(CABINET_TILE))
        cabinet.anchor.set(0.5)
        cabinet.scale.set(1.3)
        const cabinetAnchor = cabinetAnchorFor(zone as DepartmentZone)
        cabinet.position.set(cabinetAnchor.x, cabinetAnchor.y)
        app.stage.addChild(cabinet)

        const trash = new Sprite(texturesRef.current.get(TRASH_TILE))
        trash.anchor.set(0.5)
        trash.scale.set(1.1)
        const trashAnchor = trashAnchorFor(zone as DepartmentZone)
        trash.position.set(trashAnchor.x, trashAnchor.y)
        app.stage.addChild(trash)

        const art = new Sprite(texturesRef.current.get(ART_TILE))
        art.anchor.set(0.5)
        art.scale.set(1.1)
        const artAnchor = artAnchorFor(zone as DepartmentZone)
        art.position.set(artAnchor.x, artAnchor.y)
        app.stage.addChild(art)

        const plant = new Sprite(texturesRef.current.get(PLANT_TILE))
        plant.anchor.set(0.5, 0.85) // base of the plant, so sway rotation pivots at the pot
        plant.scale.set(1.3)
        const plantAnchor = plantAnchorFor(zone as DepartmentZone)
        plant.position.set(plantAnchor.x, plantAnchor.y)
        app.stage.addChild(plant)
        plantsRef.current.push(plant)
      }

      app.ticker.add(() => {
        tickRef.current += 1
        const tick = tickRef.current

        for (const plant of plantsRef.current) {
          plant.rotation = Math.sin(tick * 0.025 + plant.position.x) * 0.06
        }

        for (const sprite of spritesRef.current.values()) {
          const isActive = ACTIVE_STATUSES.includes(sprite.status)
          const isIdle = sprite.status === 'idle'
          const effectiveTarget = isIdle
            ? (() => {
                const wander = wanderOffset(sprite.bobPhase, tick)
                return { x: sprite.baseTarget.x + wander.x, y: sprite.baseTarget.y + wander.y }
              })()
            : sprite.baseTarget

          const dx = effectiveTarget.x - sprite.container.x
          const dy = effectiveTarget.y - sprite.container.y
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

          // Subtle continuous bob — applied to the sprite's own local
          // offset, never to container.x/y, so it can't interfere with the
          // walk-to-target distance check above.
          const bobAmplitude = isActive ? BOB_AMPLITUDE_ACTIVE : BOB_AMPLITUDE_IDLE
          const bobSpeed = isActive ? BOB_SPEED_ACTIVE : BOB_SPEED_IDLE
          sprite.charSprite.position.y = Math.sin(tick * bobSpeed + sprite.bobPhase) * bobAmplitude

          // Pulsing "at work" glow under active agents, at their desk.
          sprite.glow.clear()
          if (isActive) {
            const glowAlpha = 0.18 + 0.14 * (0.5 + 0.5 * Math.sin(tick * GLOW_SPEED + sprite.bobPhase))
            sprite.glow
              .ellipse(0, -2, 14, 6)
              .fill({ color: STATUS_DOT_COLOR[sprite.status] ?? 0xffd93d, alpha: glowAlpha })
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
      plantsRef.current = []
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
