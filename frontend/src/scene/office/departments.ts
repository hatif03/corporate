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
  { id: 'executive', displayName: 'Executive', x: 20, y: 20, width: 110, height: 100, color: 0xffd93d },
  { id: 'finance_audit', displayName: 'Finance & Audit', x: 150, y: 20, width: 110, height: 100, color: 0x6bcf7f },
  { id: 'engineering_sre', displayName: 'Engineering & SRE', x: 280, y: 20, width: 110, height: 100, color: 0x6c8ef5 },
  { id: 'legal_risk', displayName: 'Legal & Risk', x: 410, y: 20, width: 110, height: 100, color: 0x9b7ede },
  { id: 'hr_people_ops', displayName: 'HR & People Ops', x: 20, y: 140, width: 110, height: 100, color: 0xff6b6b },
  { id: 'customer_support', displayName: 'Customer Support', x: 150, y: 140, width: 110, height: 100, color: 0x4ecdc4 },
  { id: 'marketing_comms', displayName: 'Marketing & Comms', x: 280, y: 140, width: 110, height: 100, color: 0xff9f43 },
  { id: 'product_analytics', displayName: 'Product & Analytics', x: 410, y: 140, width: 110, height: 100, color: 0xa899b5 },
  { id: 'sales_crm', displayName: 'Sales & CRM (A2A)', x: 20, y: 260, width: 500, height: 60, color: 0xd9cfe0 },
]
