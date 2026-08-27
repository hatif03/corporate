// The data-driven department registry: adding a department to the floor is
// adding one entry here (plus the matching backend/departments/<id>
// package) — no floor-rendering code changes needed. See
// docs/system_prompt.md.
//
// Open-plan office floor (adapted from the reference app's layout
// philosophy — one continuous floor, no walled rooms — see
// /THIRD_PARTY_SKILLS.md): each department gets a desk cluster with no
// walls/doors separating it from its neighbors, plus two shared
// non-department zones (a boardroom and a break room). World size is
// derived below; OfficeFloor.tsx scales this to fit whatever screen space
// is actually available, so these are logical/world coordinates, not
// pixels.

export interface DepartmentZone {
  id: string
  displayName: string
  x: number
  y: number
  width: number
  height: number
  color: number
  kind: 'department' | 'boardroom' | 'breakroom'
}

const ROOM_W = 300
const ROOM_H = 200
const GAP = 16 // open-plan breathing room between clusters — no wall/door tile here
const MARGIN = 32
const COL_X = [MARGIN, MARGIN + ROOM_W + GAP, MARGIN + 2 * (ROOM_W + GAP)]
const ROW_Y = [MARGIN, MARGIN + ROOM_H + GAP, MARGIN + 2 * (ROOM_H + GAP), MARGIN + 3 * (ROOM_H + GAP)]

export const DEPARTMENT_ZONES: DepartmentZone[] = [
  { id: 'executive', displayName: 'Executive', x: COL_X[0], y: ROW_Y[0], width: ROOM_W, height: ROOM_H, color: 0xffd93d, kind: 'department' },
  { id: 'finance_audit', displayName: 'Finance & Audit', x: COL_X[1], y: ROW_Y[0], width: ROOM_W, height: ROOM_H, color: 0x6bcf7f, kind: 'department' },
  { id: 'engineering_sre', displayName: 'Engineering & SRE', x: COL_X[2], y: ROW_Y[0], width: ROOM_W, height: ROOM_H, color: 0x6c8ef5, kind: 'department' },
  { id: 'legal_risk', displayName: 'Legal & Risk', x: COL_X[0], y: ROW_Y[1], width: ROOM_W, height: ROOM_H, color: 0x9b7ede, kind: 'department' },
  { id: 'hr_people_ops', displayName: 'HR & People Ops', x: COL_X[1], y: ROW_Y[1], width: ROOM_W, height: ROOM_H, color: 0xff6b6b, kind: 'department' },
  { id: 'customer_support', displayName: 'Customer Support', x: COL_X[2], y: ROW_Y[1], width: ROOM_W, height: ROOM_H, color: 0x4ecdc4, kind: 'department' },
  { id: 'marketing_comms', displayName: 'Marketing & Comms', x: COL_X[0], y: ROW_Y[2], width: ROOM_W, height: ROOM_H, color: 0xff9f43, kind: 'department' },
  { id: 'product_analytics', displayName: 'Product & Analytics', x: COL_X[1], y: ROW_Y[2], width: ROOM_W, height: ROOM_H, color: 0xa899b5, kind: 'department' },
  { id: 'sales_crm', displayName: 'Sales & CRM (A2A)', x: COL_X[2], y: ROW_Y[2], width: ROOM_W, height: ROOM_H, color: 0xd9cfe0, kind: 'department' },
  // Shared zones — no agents live here (nothing has department === these
  // ids), just furniture. Boardroom spans two columns for a long table.
  { id: 'boardroom', displayName: 'Boardroom', x: COL_X[0], y: ROW_Y[3], width: ROOM_W * 2 + GAP, height: ROOM_H, color: 0xead9a0, kind: 'boardroom' },
  { id: 'breakroom', displayName: 'Break Room', x: COL_X[2], y: ROW_Y[3], width: ROOM_W, height: ROOM_H, color: 0xf3daca, kind: 'breakroom' },
]

export const WORLD_WIDTH = COL_X[2] + ROOM_W + MARGIN
export const WORLD_HEIGHT = ROW_Y[3] + ROOM_H + MARGIN
