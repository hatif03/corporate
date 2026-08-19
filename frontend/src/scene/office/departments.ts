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
  { id: 'executive', displayName: 'Executive', x: 20, y: 20, width: 140, height: 110, color: 0xffd93d },
  { id: 'finance_audit', displayName: 'Finance & Audit', x: 180, y: 20, width: 140, height: 110, color: 0x6bcf7f },
  { id: 'engineering_sre', displayName: 'Engineering & SRE', x: 340, y: 20, width: 140, height: 110, color: 0x6c8ef5 },
  { id: 'legal_risk', displayName: 'Legal & Risk', x: 20, y: 150, width: 140, height: 110, color: 0x9b7ede },
  { id: 'hr_people_ops', displayName: 'HR & People Ops', x: 180, y: 150, width: 140, height: 110, color: 0xff6b6b },
  { id: 'customer_support', displayName: 'Customer Support', x: 340, y: 150, width: 140, height: 110, color: 0x4ecdc4 },
  { id: 'sales_crm', displayName: 'Sales & CRM (A2A)', x: 20, y: 280, width: 460, height: 60, color: 0xff9f43 },
]
