// Corridor rectangles connecting the 3x3 room grid (departments.ts) — kept
// separate from the per-department registry since corridors aren't owned by
// any one department. Rendered as their own tinted floor strips in
// OfficeFloor.tsx, underneath the room floors.

import { DEPARTMENT_ZONES } from './departments'

export interface CorridorRect {
  x: number
  y: number
  width: number
  height: number
}

const ROOM_W = 460
const ROOM_H = 300
const CORRIDOR = 60

function zoneAt(col: number, row: number) {
  // Rooms are laid out row-major in DEPARTMENT_ZONES (see departments.ts).
  return DEPARTMENT_ZONES[row * 3 + col]
}

export const CORRIDOR_RECTS: CorridorRect[] = (() => {
  const rects: CorridorRect[] = []
  // Horizontal corridors: between column 0/1 and 1/2, for every row.
  for (let row = 0; row < 3; row++) {
    const r0 = zoneAt(0, row)
    const r1 = zoneAt(1, row)
    const r2 = zoneAt(2, row)
    rects.push({ x: r0.x + ROOM_W, y: r0.y, width: CORRIDOR, height: ROOM_H })
    rects.push({ x: r1.x + ROOM_W, y: r1.y, width: CORRIDOR, height: ROOM_H })
    void r2
  }
  // Vertical corridors: between row 0/1 and 1/2, for every column.
  for (let col = 0; col < 3; col++) {
    const c0 = zoneAt(col, 0)
    const c1 = zoneAt(col, 1)
    rects.push({ x: c0.x, y: c0.y + ROOM_H, width: ROOM_W, height: CORRIDOR })
    rects.push({ x: c1.x, y: c1.y + ROOM_H, width: ROOM_W, height: CORRIDOR })
  }
  return rects
})()
