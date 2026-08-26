// The data-driven department registry: adding a department to the floor is
// adding one entry here (plus the matching backend/departments/<id> package)
// — no floor-rendering code changes needed. See docs/system_prompt.md.
//
// Real 3x3 room-and-corridor office layout (see corridors.ts for the
// connecting hallways) — replaces the earlier thin-strip zones. World size
// is 1580x1100; OfficeFloor.tsx scales this to fit whatever screen space is
// actually available, so these are logical/world coordinates, not pixels.

export interface DepartmentZone {
  id: string
  displayName: string
  x: number
  y: number
  width: number
  height: number
  color: number
}

const ROOM_W = 460
const ROOM_H = 300
const CORRIDOR = 60
const MARGIN = 40
const COL_X = [MARGIN, MARGIN + ROOM_W + CORRIDOR, MARGIN + 2 * (ROOM_W + CORRIDOR)]
const ROW_Y = [MARGIN, MARGIN + ROOM_H + CORRIDOR, MARGIN + 2 * (ROOM_H + CORRIDOR)]

export const DEPARTMENT_ZONES: DepartmentZone[] = [
  { id: 'executive', displayName: 'Executive', x: COL_X[0], y: ROW_Y[0], width: ROOM_W, height: ROOM_H, color: 0xffd93d },
  { id: 'finance_audit', displayName: 'Finance & Audit', x: COL_X[1], y: ROW_Y[0], width: ROOM_W, height: ROOM_H, color: 0x6bcf7f },
  { id: 'engineering_sre', displayName: 'Engineering & SRE', x: COL_X[2], y: ROW_Y[0], width: ROOM_W, height: ROOM_H, color: 0x6c8ef5 },
  { id: 'legal_risk', displayName: 'Legal & Risk', x: COL_X[0], y: ROW_Y[1], width: ROOM_W, height: ROOM_H, color: 0x9b7ede },
  { id: 'hr_people_ops', displayName: 'HR & People Ops', x: COL_X[1], y: ROW_Y[1], width: ROOM_W, height: ROOM_H, color: 0xff6b6b },
  { id: 'customer_support', displayName: 'Customer Support', x: COL_X[2], y: ROW_Y[1], width: ROOM_W, height: ROOM_H, color: 0x4ecdc4 },
  { id: 'marketing_comms', displayName: 'Marketing & Comms', x: COL_X[0], y: ROW_Y[2], width: ROOM_W, height: ROOM_H, color: 0xff9f43 },
  { id: 'product_analytics', displayName: 'Product & Analytics', x: COL_X[1], y: ROW_Y[2], width: ROOM_W, height: ROOM_H, color: 0xa899b5 },
  { id: 'sales_crm', displayName: 'Sales & CRM (A2A)', x: COL_X[2], y: ROW_Y[2], width: ROOM_W, height: ROOM_H, color: 0xd9cfe0 },
]

export const WORLD_WIDTH = COL_X[2] + ROOM_W + MARGIN
export const WORLD_HEIGHT = ROW_Y[2] + ROOM_H + MARGIN
