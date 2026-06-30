'use client'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface Props {
  taskId: string
  severity: number
}

interface Cascade {
  cascade_severity: number
  at_risk_titles?: string[]
  critical_path_affected?: boolean
}

export default function CascadeBadge({ taskId, severity }: Props) {
  const { token } = useAuth()
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<Cascade | null>(null)
  const [loading, setLoading] = useState(false)

  if (severity < 1) return null

  const toggle = async () => {
    if (open) { setOpen(false); return }
    setOpen(true)
    if (data || !token) return
    setLoading(true)
    try {
      setData(await api.getCascade(token, taskId))
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-3 pt-3 border-t border-navy/5">
      <button onClick={toggle} className="flex items-center gap-1.5 text-left">
        <span className="text-[11px]">🌊</span>
        <span className="text-[11px] text-navy/45 font-body hover:text-navy/70 transition-colors">
          Delays {severity} other task{severity === 1 ? '' : 's'}
        </span>
        {data?.critical_path_affected && (
          <span className="skill-badge" style={{ background: '#FCEDE9', color: '#E08A76' }}>critical path</span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-2 pl-5">
              {loading ? (
                <p className="text-[11px] text-navy/40 font-body">Tracing the cascade…</p>
              ) : data?.at_risk_titles && data.at_risk_titles.length > 0 ? (
                <ul className="space-y-1">
                  {data.at_risk_titles.map((title, i) => (
                    <li key={i} className="flex items-center gap-1.5 text-[12px] text-navy/60 font-body">
                      <span className="text-navy/25">↳</span> {title}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[11px] text-navy/40 font-body">No downstream tasks.</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
