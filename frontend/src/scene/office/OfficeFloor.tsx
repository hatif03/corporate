import { useEffect, useRef } from 'react'
import { Application, Assets, Container, Graphics, Sprite, Text, Texture, TilingSprite } from 'pixi.js'
import { DEPARTMENT_ZONES, WORLD_HEIGHT, WORLD_WIDTH, type DepartmentZone } from './departments'
import { CORRIDOR_RECTS } from './corridors'
import {
  ART_TILE,
  BOOKSHELF_TILE,
  CABINET_TILE,
  CHARACTER_VARIANTS,
  CORRIDOR_FLOOR_TILE,
  DESK_TILE,
  DOOR_TILE,
  FLOOR_TILE,
  PLANT_TILE,
  TRASH_TILE,
  WALL_TILE,
  variantForCharacter,
} from './tileset'
import {
  artAnchorFor,
  bookshelfAnchorFor,
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
const WALL_THICKNESS = 16 // px, tiled strip along each room's north edge

interface AgentSprite {
  container: Container
  charSprite: Sprite
  statusDot: Graphics
  glow: Graphics
  baseTarget: { x: number; y: number }
  departmentId: string
  character: string
  status: AgentStatus
  walkFrame: 0 | 1
  tickCount: number
  bobPhase: number
}

/**
 * Real tile/sprite office floor (Kenney CC0 RPG Urban Pack, see tileset.ts):
 * a genuine 3x3 room-and-corridor layout (departments.ts / corridors.ts),
 * tiled walls + doors, a small furniture set per room (desk, cabinet,
 * bookshelf, plant, trash, wall art), and one character sprite per agent
 * that walks between a "desk" and "idle" anchor as its status changes
 * (movement.ts — pure client-side, see ADR-0013). Agents are diffed against
 * the previous frame instead of being torn down and rebuilt on every
 * Firestore tick, so an in-progress walk is never interrupted.
 *
 * Everything is drawn into a single `world` container, which is rescaled
 * and centered to fit whatever screen space the host panel actually has
 * (Pixi v8's native `resizeTo`, plus our own fit-to-container pass) — the
 * scene is a fixed logical size (WORLD_WIDTH x WORLD_HEIGHT), never a fixed
 * pixel size.
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
  const worldRef = useRef<Container | null>(null)
  const readyRef = useRef(false)
  const spritesRef = useRef<Map<string, AgentSprite>>(new Map())
  const texturesRef = useRef<Map<string, Texture>>(new Map())
  const plantsRef = useRef<Sprite[]>([])
  const tickRef = useRef(0)
  const agentsRef = useRef<Agent[]>(agents)
  agentsRef.current = agents

  function fitWorld() {
    const world = worldRef.current
    const el = containerRef.current
    if (!world || !el) return
    const w = el.clientWidth
    const h = el.clientHeight
    if (w === 0 || h === 0) return
    const scale = Math.min(w / WORLD_WIDTH, h / WORLD_HEIGHT)
    world.scale.set(scale)
    world.position.set((w - WORLD_WIDTH * scale) / 2, (h - WORLD_HEIGHT * scale) / 2)
  }

  function reconcile(currentAgents: Agent[]) {
    const world = worldRef.current
    const textures = texturesRef.current
    if (!world || !readyRef.current) return

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
          const variant = variantForCharacter(agent.character, agent.department)
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

          world.addChild(container)
          sprite = {
            container,
            charSprite,
            statusDot,
            glow,
            baseTarget,
            departmentId: agent.department,
            character: agent.character,
            status: agent.status,
            walkFrame: 0,
            tickCount: 0,
            bobPhase: (hashId(agent.id) % 1000) / 1000 * Math.PI * 2,
          }
          spritesRef.current.set(agent.id, sprite)
        }

        sprite.baseTarget = baseTarget
        sprite.departmentId = agent.department
        sprite.character = agent.character
        sprite.status = agent.status
        const variant = variantForCharacter(agent.character, agent.department)
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
      await app.init({ resizeTo: containerRef.current ?? undefined, backgroundColor: 0xf4f1ea, antialias: true })
      if (destroyed || !containerRef.current) {
        app.destroy(true)
        return
      }
      containerRef.current.appendChild(app.canvas)

      const world = new Container()
      app.stage.addChild(world)
      worldRef.current = world

      const allSprites = [
        FLOOR_TILE,
        DESK_TILE,
        CABINET_TILE,
        BOOKSHELF_TILE,
        PLANT_TILE,
        TRASH_TILE,
        ART_TILE,
        WALL_TILE,
        DOOR_TILE,
        CORRIDOR_FLOOR_TILE,
        ...CHARACTER_VARIANTS.flatMap((v) => [v.idle, v.walkA, v.walkB]),
      ]
      const loaded = (await Assets.load(allSprites)) as Record<string, Texture>
      for (const [url, texture] of Object.entries(loaded)) texturesRef.current.set(url, texture)
      if (destroyed) return

      // Corridors first, underneath the rooms.
      for (const rect of CORRIDOR_RECTS) {
        const floor = new TilingSprite({
          texture: texturesRef.current.get(CORRIDOR_FLOOR_TILE),
          width: rect.width,
          height: rect.height,
        })
        floor.position.set(rect.x, rect.y)
        world.addChild(floor)
      }

      for (const zone of DEPARTMENT_ZONES) {
        const floor = new TilingSprite({
          texture: texturesRef.current.get(FLOOR_TILE),
          width: zone.width,
          height: zone.height,
        })
        floor.position.set(zone.x, zone.y)
        floor.tint = zone.color
        floor.alpha = 0.55
        world.addChild(floor)

        // Tiled wall along the room's north edge.
        const wall = new TilingSprite({
          texture: texturesRef.current.get(WALL_TILE),
          width: zone.width,
          height: WALL_THICKNESS,
        })
        wall.position.set(zone.x, zone.y)
        world.addChild(wall)

        // Door on the south edge, facing the corridor system.
        const door = new Sprite(texturesRef.current.get(DOOR_TILE))
        door.anchor.set(0.5, 1)
        door.scale.set(1.6)
        door.position.set(zone.x + zone.width * 0.5, zone.y + zone.height)
        world.addChild(door)

        // Heavier double-line border on top of the wall/door art, matching
        // the app's existing hard-shadow/inset-border design language.
        const border = new Graphics()
          .rect(zone.x, zone.y, zone.width, zone.height)
          .stroke({ width: 3, color: 0x2b2b2b })
          .rect(zone.x + 4, zone.y + 4, zone.width - 8, zone.height - 8)
          .stroke({ width: 1, color: 0x2b2b2b, alpha: 0.4 })
        world.addChild(border)

        const label = new Text({
          text: zone.displayName,
          style: { fontSize: 14, fill: 0x1c1c1c, fontWeight: 'bold' },
        })
        label.position.set(zone.x + 10, zone.y + WALL_THICKNESS + 6)
        world.addChild(label)

        const desk = new Sprite(texturesRef.current.get(DESK_TILE))
        desk.anchor.set(0.5)
        desk.scale.set(1.6)
        const deskAnchor = deskAnchorFor(zone as DepartmentZone)
        desk.position.set(deskAnchor.x, deskAnchor.y + 10)
        world.addChild(desk)

        const cabinet = new Sprite(texturesRef.current.get(CABINET_TILE))
        cabinet.anchor.set(0.5)
        cabinet.scale.set(1.3)
        const cabinetAnchor = cabinetAnchorFor(zone as DepartmentZone)
        cabinet.position.set(cabinetAnchor.x, cabinetAnchor.y)
        world.addChild(cabinet)

        const bookshelf = new Sprite(texturesRef.current.get(BOOKSHELF_TILE))
        bookshelf.anchor.set(0.5)
        bookshelf.scale.set(1.3)
        const bookshelfAnchor = bookshelfAnchorFor(zone as DepartmentZone)
        bookshelf.position.set(bookshelfAnchor.x, bookshelfAnchor.y)
        world.addChild(bookshelf)

        const trash = new Sprite(texturesRef.current.get(TRASH_TILE))
        trash.anchor.set(0.5)
        trash.scale.set(1.1)
        const trashAnchor = trashAnchorFor(zone as DepartmentZone)
        trash.position.set(trashAnchor.x, trashAnchor.y)
        world.addChild(trash)

        const art = new Sprite(texturesRef.current.get(ART_TILE))
        art.anchor.set(0.5)
        art.scale.set(1.1)
        const artAnchor = artAnchorFor(zone as DepartmentZone)
        art.position.set(artAnchor.x, artAnchor.y)
        world.addChild(art)

        const plant = new Sprite(texturesRef.current.get(PLANT_TILE))
        plant.anchor.set(0.5, 0.85) // base of the plant, so sway rotation pivots at the pot
        plant.scale.set(1.3)
        const plantAnchor = plantAnchorFor(zone as DepartmentZone)
        plant.position.set(plantAnchor.x, plantAnchor.y)
        world.addChild(plant)
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
              const variant = variantForCharacter(sprite.character, sprite.departmentId)
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
      fitWorld()
      reconcile(agentsRef.current)
    }

    void setup()

    const resizeObserver = new ResizeObserver(() => fitWorld())
    if (containerRef.current) resizeObserver.observe(containerRef.current)

    return () => {
      destroyed = true
      readyRef.current = false
      resizeObserver.disconnect()
      spritesRef.current.clear()
      plantsRef.current = []
      worldRef.current = null
      app.destroy(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    reconcile(agents)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
