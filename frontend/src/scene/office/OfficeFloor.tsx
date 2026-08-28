import { useEffect, useRef, useState } from 'react'
import { Application, Assets, Container, Graphics, Sprite, Text, Texture, TilingSprite } from 'pixi.js'
import { Icon } from '../../components/Icon'
import { generateBreakroomMusic } from '../../lib/platformClient'
import { DEPARTMENT_ZONES, SOCIAL_POINT, WORLD_HEIGHT, WORLD_WIDTH, type DepartmentZone } from './departments'
import {
  ART_TILE,
  BOOKSHELF_TILE,
  CABINET_TILE,
  CHARACTER_VARIANTS,
  DESK_TILE,
  FLOOR_TILE,
  PLANT_TILE,
  TRASH_TILE,
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

const MOVE_SPEED = 1.1 // px/frame at 60fps — tuned for the office's tighter room scale
const WALK_PHASE_TICKS = 8 // how often to advance one step of the walk cycle
// Stand -> step -> stand -> step, not a continuous A/B alternation — matches
// the reference app's 4-phase walk cycle (see /THIRD_PARTY_SKILLS.md),
// reusing our idle/walkA/walkB frames in place of its 3-row directional set.
const WALK_CYCLE: readonly ('idle' | 'walkA' | 'walkB')[] = ['idle', 'walkA', 'idle', 'walkB']
const BOB_AMPLITUDE_IDLE = 1.2 // px — a subtle "breathing" bob so nobody ever looks frozen
const BOB_AMPLITUDE_ACTIVE = 2.2 // px — a slightly busier bob while actively working
const BOB_SPEED_IDLE = 0.05 // radians/frame
const BOB_SPEED_ACTIVE = 0.11 // radians/frame
const GLOW_SPEED = 0.06 // radians/frame — pulsing "at work" glow under active agents

// Ambient "water cooler" social behavior: purely a client-side visual flourish
// (no backend AgentStatus involved) — every so often, two currently-idle
// agents get pulled to a shared spot for a few seconds with a chat-bubble
// icon, then released back to normal idle/wander. ponytail: if an agent's
// real status flips to active mid-chat, the visual pairing is left to just
// run out on its own timer rather than being cancelled early — it's decorative
// only, so the mismatch is harmless and not worth the extra bookkeeping.
const SOCIAL_CHECK_INTERVAL = 900 // ticks (~15s at 60fps) between "should a chat start?" rolls
const SOCIAL_DURATION_TICKS = 360 // ~6s per chat
const SOCIAL_TRIGGER_CHANCE = 0.35

interface AgentSprite {
  container: Container
  charSprite: Sprite
  statusDot: Graphics
  glow: Graphics
  chatBubble: Graphics
  baseTarget: { x: number; y: number }
  departmentId: string
  character: string
  status: AgentStatus
  walkPhase: number
  tickCount: number
  bobPhase: number
}

/**
 * Real tile/sprite office floor (Kenney CC0 RPG Urban Pack, see tileset.ts):
 * one open-plan floor — desk clusters per department with no walls/doors
 * between them, plus a shared boardroom and break room — adapted from the
 * reference app's open-plan layout philosophy (see /THIRD_PARTY_SKILLS.md).
 * One character sprite per agent walks between a "desk" and "idle" anchor
 * as its status changes (movement.ts — pure client-side, see ADR-0013).
 * Agents are diffed against the previous frame instead of being torn down
 * and rebuilt on every Firestore tick, so an in-progress walk is never
 * interrupted.
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
 * The Pixi ticker is stopped (not the whole app) whenever the tab is
 * hidden, so an invisible canvas doesn't keep burning GPU/CPU.
 */
export function OfficeFloor({ agents, orgId }: { agents: Agent[]; orgId: string }) {
  const [musicUrl, setMusicUrl] = useState<string | null>(null)
  const [musicBusy, setMusicBusy] = useState(false)

  async function playBreakroomMusic() {
    setMusicBusy(true)
    try {
      const { url } = await generateBreakroomMusic(orgId)
      setMusicUrl(url)
    } finally {
      setMusicBusy(false)
    }
  }

  const containerRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<Application | null>(null)
  const worldRef = useRef<Container | null>(null)
  const readyRef = useRef(false)
  const spritesRef = useRef<Map<string, AgentSprite>>(new Map())
  const texturesRef = useRef<Map<string, Texture>>(new Map())
  const plantsRef = useRef<Sprite[]>([])
  const socialPairsRef = useRef<Map<string, { until: number; offsetX: number }>>(new Map())
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
          charSprite.scale.set(1.85)
          container.addChild(charSprite)

          const statusDot = new Graphics()
          container.addChild(statusDot)

          const chatBubble = new Graphics()
          container.addChild(chatBubble)

          world.addChild(container)
          sprite = {
            container,
            charSprite,
            statusDot,
            glow,
            chatBubble,
            baseTarget,
            departmentId: agent.department,
            character: agent.character,
            status: agent.status,
            walkPhase: 0,
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
        ...CHARACTER_VARIANTS.flatMap((v) => [v.idle, v.walkA, v.walkB]),
      ]
      const loaded = (await Assets.load(allSprites)) as Record<string, Texture>
      for (const [url, texture] of Object.entries(loaded)) texturesRef.current.set(url, texture)
      if (destroyed) return

      // One continuous floor underneath every zone — open plan, no walls.
      // A large tileScale is the whole trick here: the source tile is a
      // native 16px texture, and tiling it at 1:1 across a ~1400px-wide
      // world repeats it ~90 times per row — that dense visible grid *is*
      // the "cluttered" look. Scaling the tile up reads as a calm textured
      // surface instead of a busy checkerboard, at the same real art.
      const baseFloor = new TilingSprite({ texture: texturesRef.current.get(FLOOR_TILE), width: WORLD_WIDTH, height: WORLD_HEIGHT })
      baseFloor.tileScale.set(6)
      baseFloor.tint = 0xfaf3e2
      world.addChild(baseFloor)

      for (const zone of DEPARTMENT_ZONES) {
        // One open floor, no per-zone walls/tint/border — desk clusters
        // just sit close together (departments.ts). A small floating label
        // (no background chip, no outline) is the only thing marking which
        // cluster belongs to which department, so agents can still be
        // told apart at a glance without it reading as a separate room.
        const label = new Text({
          text: zone.displayName,
          style: { fontFamily: 'Inter, sans-serif', fontSize: 13, fill: 0x6b6458, fontWeight: '600' },
        })
        label.position.set(zone.x + 14, zone.y + 10)
        label.alpha = 0.85
        world.addChild(label)

        const FURNITURE_SCALE = 2.1

        if (zone.kind === 'department') {
          const desk = new Sprite(texturesRef.current.get(DESK_TILE))
          desk.anchor.set(0.5)
          desk.scale.set(FURNITURE_SCALE)
          const deskAnchor = deskAnchorFor(zone as DepartmentZone)
          desk.position.set(deskAnchor.x, deskAnchor.y + 10)
          world.addChild(desk)

          const cabinet = new Sprite(texturesRef.current.get(CABINET_TILE))
          cabinet.anchor.set(0.5)
          cabinet.scale.set(FURNITURE_SCALE * 0.85)
          const cabinetAnchor = cabinetAnchorFor(zone as DepartmentZone)
          cabinet.position.set(cabinetAnchor.x, cabinetAnchor.y)
          world.addChild(cabinet)

          const bookshelf = new Sprite(texturesRef.current.get(BOOKSHELF_TILE))
          bookshelf.anchor.set(0.5)
          bookshelf.scale.set(FURNITURE_SCALE * 0.85)
          const bookshelfAnchor = bookshelfAnchorFor(zone as DepartmentZone)
          bookshelf.position.set(bookshelfAnchor.x, bookshelfAnchor.y)
          world.addChild(bookshelf)

          const trash = new Sprite(texturesRef.current.get(TRASH_TILE))
          trash.anchor.set(0.5)
          trash.scale.set(FURNITURE_SCALE * 0.7)
          const trashAnchor = trashAnchorFor(zone as DepartmentZone)
          trash.position.set(trashAnchor.x, trashAnchor.y)
          world.addChild(trash)

          const art = new Sprite(texturesRef.current.get(ART_TILE))
          art.anchor.set(0.5)
          art.scale.set(FURNITURE_SCALE * 0.7)
          const artAnchor = artAnchorFor(zone as DepartmentZone)
          art.position.set(artAnchor.x, artAnchor.y)
          world.addChild(art)
        } else if (zone.kind === 'boardroom') {
          // A long table: three desk tiles in a row, nobody permanently
          // seated (no agent has department === 'boardroom').
          for (let i = 0; i < 3; i++) {
            const table = new Sprite(texturesRef.current.get(DESK_TILE))
            table.anchor.set(0.5)
            table.scale.set(FURNITURE_SCALE)
            table.position.set(zone.x + zone.width * (0.2 + i * 0.3), zone.y + zone.height * 0.55)
            world.addChild(table)
          }
          const art = new Sprite(texturesRef.current.get(ART_TILE))
          art.anchor.set(0.5)
          art.scale.set(FURNITURE_SCALE * 0.7)
          art.position.set(zone.x + zone.width * 0.5, zone.y + zone.height * 0.18)
          world.addChild(art)
        } else {
          // Break room: cabinet + bookshelf + trash + plant, no desk.
          const cabinet = new Sprite(texturesRef.current.get(CABINET_TILE))
          cabinet.anchor.set(0.5)
          cabinet.scale.set(FURNITURE_SCALE * 0.85)
          cabinet.position.set(zone.x + zone.width * 0.25, zone.y + zone.height * 0.5)
          world.addChild(cabinet)

          const bookshelf = new Sprite(texturesRef.current.get(BOOKSHELF_TILE))
          bookshelf.anchor.set(0.5)
          bookshelf.scale.set(FURNITURE_SCALE * 0.85)
          bookshelf.position.set(zone.x + zone.width * 0.75, zone.y + zone.height * 0.32)
          world.addChild(bookshelf)

          const trash = new Sprite(texturesRef.current.get(TRASH_TILE))
          trash.anchor.set(0.5)
          trash.scale.set(FURNITURE_SCALE * 0.7)
          trash.position.set(zone.x + zone.width * 0.5, zone.y + zone.height * 0.78)
          world.addChild(trash)
        }

        const plant = new Sprite(texturesRef.current.get(PLANT_TILE))
        plant.anchor.set(0.5, 0.85) // base of the plant, so sway rotation pivots at the pot
        plant.scale.set(FURNITURE_SCALE * 0.85)
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

        // Water-cooler social behavior: roll for a new chat every so often,
        // picking two currently-idle agents at random (see the const block
        // above this component for the tuning knobs).
        if (tick % SOCIAL_CHECK_INTERVAL === 0 && Math.random() < SOCIAL_TRIGGER_CHANCE) {
          const stillChatting = [...socialPairsRef.current.values()].some((p) => tick < p.until)
          if (!stillChatting) {
            const idleIds = [...spritesRef.current.entries()].filter(([, s]) => s.status === 'idle').map(([id]) => id)
            if (idleIds.length >= 2) {
              const a = idleIds[Math.floor(Math.random() * idleIds.length)]
              let b = a
              for (let guard = 0; guard < 5 && b === a; guard++) b = idleIds[Math.floor(Math.random() * idleIds.length)]
              if (b !== a) {
                const until = tick + SOCIAL_DURATION_TICKS
                socialPairsRef.current.set(a, { until, offsetX: -12 })
                socialPairsRef.current.set(b, { until, offsetX: 12 })
              }
            }
          }
        }

        for (const [agentId, sprite] of spritesRef.current.entries()) {
          const isActive = ACTIVE_STATUSES.includes(sprite.status)
          const isIdle = sprite.status === 'idle'
          const social = socialPairsRef.current.get(agentId)
          const inSocial = social && tick < social.until
          if (social && !inSocial) socialPairsRef.current.delete(agentId)

          const effectiveTarget = inSocial
            ? { x: SOCIAL_POINT.x + social.offsetX, y: SOCIAL_POINT.y }
            : isIdle
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
            if (sprite.tickCount >= WALK_PHASE_TICKS) {
              sprite.tickCount = 0
              sprite.walkPhase = (sprite.walkPhase + 1) % WALK_CYCLE.length
              const variant = variantForCharacter(sprite.character, sprite.departmentId)
              const frame = WALK_CYCLE[sprite.walkPhase]
              const walkTexture = frame === 'idle' ? variant.idle : frame === 'walkA' ? variant.walkA : variant.walkB
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

          // Small hand-drawn speech bubble (no emoji, per this project's
          // icon convention) over anyone currently in a water-cooler chat.
          sprite.chatBubble.clear()
          if (inSocial) {
            const bobbleY = -38
            sprite.chatBubble
              .roundRect(-9, bobbleY - 7, 18, 12, 4)
              .fill({ color: 0xfffdf5, alpha: 0.95 })
              .stroke({ width: 1, color: 0x6b6458, alpha: 0.5 })
            for (const dotX of [-4, 0, 4]) {
              sprite.chatBubble.circle(dotX, bobbleY - 1, 1.2).fill({ color: 0x6b6458, alpha: 0.8 })
            }
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

    // Stop the ticker (not the whole app) while the tab is hidden — no
    // point burning GPU/CPU animating a canvas nobody can see, and the
    // scene graph/WebGL context stay warm for an instant resume.
    const onVisibilityChange = () => {
      if (!appRef.current) return
      if (document.hidden) appRef.current.ticker.stop()
      else appRef.current.ticker.start()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      destroyed = true
      readyRef.current = false
      resizeObserver.disconnect()
      document.removeEventListener('visibilitychange', onVisibilityChange)
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

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <div style={{ position: 'absolute', right: 12, bottom: 12, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
        {musicUrl && <audio src={musicUrl} controls autoPlay style={{ height: 32 }} />}
        <button className="corp-button" onClick={playBreakroomMusic} disabled={musicBusy} title="Generate break room music (Lyria)">
          <Icon name="music" style={{ marginRight: 4, verticalAlign: -2 }} />
          {musicBusy ? 'Generating…' : 'Break room music'}
        </button>
      </div>
    </div>
  )
}
