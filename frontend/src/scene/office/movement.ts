// Pure client-side "walk to your desk" movement — no backend involvement,
// no persisted seat. scripts/seed.py creates exactly one Agent per
// department (plus the CEO), so there's no real desk-contention problem to
// solve yet; a full seat-pool claim/release system would be solving a
// problem this app doesn't have. See ADR-0013's office-floor section.
//
// ponytail: seat assignment here is a pure function of (department, sorted
// agent ids) — every client computes the identical anchor with zero
// coordination, which is what makes "no persisted seat" safe even though it
// looks like it should need one. If the roster ever grows multiple agents
// per department, or needs cross-session desk stickiness, promote the
// already-existing-but-unused Agent.currentStation field to source of
// truth via the backend's store.update_agent_status instead.

import type { Agent, AgentStatus } from '../../lib/types'
import type { DepartmentZone } from './departments'

export interface Point {
  x: number
  y: number
}

const ACTIVE_STATUSES: AgentStatus[] = ['thinking', 'working', 'typing', 'looping', 'compacting']

const AGENT_STRIDE = 24

export function deskAnchorFor(zone: DepartmentZone, indexInZone = 0): Point {
  return { x: zone.x + zone.width * 0.6 + indexInZone * AGENT_STRIDE, y: zone.y + zone.height * 0.55 }
}

export function idleAnchorFor(zone: DepartmentZone, indexInZone = 0): Point {
  return { x: zone.x + zone.width * 0.2 + indexInZone * AGENT_STRIDE, y: zone.y + zone.height * 0.8 }
}

// Fixed decorative-furniture placements, one set per zone — corners chosen
// to stay clear of the desk/idle anchors above regardless of zone size
// (the sales_crm zone is a wide short strip, everything else is roughly
// square, fractional placement handles both).
export function cabinetAnchorFor(zone: DepartmentZone): Point {
  return { x: zone.x + zone.width * 0.12, y: zone.y + zone.height * 0.3 }
}

export function plantAnchorFor(zone: DepartmentZone): Point {
  return { x: zone.x + zone.width * 0.92, y: zone.y + zone.height * 0.3 }
}

export function trashAnchorFor(zone: DepartmentZone): Point {
  return { x: zone.x + zone.width * 0.92, y: zone.y + zone.height * 0.85 }
}

export function artAnchorFor(zone: DepartmentZone): Point {
  return { x: zone.x + zone.width * 0.5, y: zone.y + zone.height * 0.12 }
}

export function hashId(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0
  return Math.abs(hash)
}

const WANDER_RADIUS = 10 // px
const WANDER_SPEED = 0.012 // radians/frame at 60fps — a full loop every ~9s

/** A small, smooth, per-agent drift around an idle anchor so agents milling
 * about never look frozen in place — deterministic per (phase, tick) so it
 * needs no server state, same "pure function, no coordination" approach as
 * the rest of this module. `phase` should be a stable per-agent value (see
 * `hashId` above) so the same agent always wanders the same pattern rather
 * than jumping every reconcile. Only meant for idle-status agents; active
 * agents stay put at their desk (see OfficeFloor.tsx's ticker). */
export function wanderOffset(phase: number, tick: number): Point {
  const t = tick * WANDER_SPEED + phase
  return { x: Math.cos(t) * WANDER_RADIUS, y: Math.sin(t * 1.3) * WANDER_RADIUS * 0.6 }
}

/** Which anchor an agent should be walking toward right now, given its
 * current status and its stable index among other agents in the same zone
 * (from a `.sort()`-ed filter of the full agent list — see OfficeFloor.tsx). */
export function getTargetPosition(agent: Agent, zone: DepartmentZone, indexInZone: number): Point {
  if (ACTIVE_STATUSES.includes(agent.status)) return deskAnchorFor(zone, indexInZone)
  if (agent.status === 'idle' || agent.status === 'ghost') return idleAnchorFor(zone, indexInZone)
  // waiting/blocked/success: nothing about these implies leaving the desk —
  // stay put rather than forcing a walk.
  return deskAnchorFor(zone, indexInZone)
}
