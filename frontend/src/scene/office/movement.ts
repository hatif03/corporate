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
