// The data-driven department registry: adding a department to the floor is
// adding one entry here (plus the matching backend/departments/<id> package)
// — no floor-rendering code changes needed. See docs/system_prompt.md.

export interface DepartmentZone {
  id: string
  displayName: string
  x: number
  y: number
  width: number
  height: number
  color: number
}

export const DEPARTMENT_ZONES: DepartmentZone[] = [
  { id: 'executive', displayName: 'Executive', x: 20, y: 20, width: 200, height: 120, color: 0xffd93d },
  { id: 'finance_audit', displayName: 'Finance & Audit', x: 240, y: 20, width: 200, height: 120, color: 0x6bcf7f },
]
