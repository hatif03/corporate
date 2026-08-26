import { useState, type ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'

export function Collapsible({
  title,
  defaultOpen = false,
  children,
}: {
  title: ReactNode
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ marginBottom: 12 }}>
      <button
        className="corp-button"
        style={{ width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 8 }}
        onClick={() => setOpen((o) => !o)}
      >
        <ChevronRight
          size={14}
          aria-hidden
          style={{ transition: 'transform 90ms steps(2, end)', transform: open ? 'rotate(90deg)' : 'none' }}
        />
        {title}
      </button>
      {open && <div style={{ padding: 'var(--corp-space-3) 0 0' }}>{children}</div>}
    </div>
  )
}
