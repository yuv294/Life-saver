'use client'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface Plan {
  task_id: string
  task_title: string
  days_overdue: number
  summary: string
  reorder: string[]
  deprioritize?: string
  at_risk_titles?: string[]
  critical_path_affected?: boolean
}

export default function OverdueRecovery() {
  const { token } = useAuth()
  const [plan, setPlan] = useState<Plan | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!token) return
    api.getResequence(token).then(r => setPlan(r.plans?.[0] ?? null)).catch(() => {})
  }, [token])

  if (!plan) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="glass-card p-5"
      style={{ borderLeft: '3px solid #E08A76' }}
    >
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-2 text-left">
        <span>⚠️</span>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-navy font-body">
            “{plan.task_title}” is {plan.days_overdue} day{plan.days_overdue === 1 ? '' : 's'} overdue
          </p>
          <p className="text-[12px] text-navy/50 font-body">Tap for a recovery plan{plan.critical_path_affected ? ' · on critical path' : ''}</p>
        </div>
        <span className="text-navy/30 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }} className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-navy/8 space-y-2.5">
              <p className="text-[12.5px] text-navy/70 font-body leading-relaxed">{plan.summary}</p>
              <div>
                <p className="text-[10px] uppercase tracking-widest text-navy/35 font-body mb-1">Re-sequence</p>
                <ol className="space-y-1">
                  {plan.reorder.map((step, i) => (
                    <li key={i} className="flex gap-2 text-[12.5px] text-navy/70 font-body">
                      <span className="text-night-blue font-medium">{i + 1}.</span> {step}
                    </li>
                  ))}
                </ol>
              </div>
              {plan.deprioritize && (
                <div className="rounded-xl p-2.5" style={{ background: 'rgba(232,160,144,0.12)' }}>
                  <p className="text-[10px] uppercase tracking-widest font-body mb-0.5" style={{ color: '#C55A5A' }}>Make room</p>
                  <p className="text-[12px] text-navy/65 font-body">{plan.deprioritize}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
