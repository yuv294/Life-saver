'use client'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface Diagnosis {
  trigger: string
  trigger_explanation: string
  intervention: string
  first_step: string
  estimated_start_minutes?: number
  anti_list_candidate?: boolean
}

const TRIGGER_STYLE: Record<string, { bg: string; fg: string; emoji: string }> = {
  ambiguity:   { bg: 'transparent', fg: '#6E94E0', emoji: '🌫️' },
  fear:        { bg: 'transparent', fg: '#A98AD6', emoji: '🛡️' },
  overwhelm:   { bg: 'transparent', fg: '#DE8068', emoji: '🌊' },
  boredom:     { bg: 'transparent', fg: '#8FA0C0', emoji: '💤' },
  resentment:  { bg: 'transparent', fg: '#CF9A2E', emoji: '🔥' },
}

interface Props {
  taskId: string
  onStartFirstStep?: () => void
}

export default function ProcrastinationInsight({ taskId, onStartFirstStep }: Props) {
  const { token } = useAuth()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [d, setD] = useState<Diagnosis | null>(null)
  const [error, setError] = useState(false)

  const analyze = async () => {
    if (!token) return
    if (open) { setOpen(false); return }
    setOpen(true)
    if (d) return
    setLoading(true)
    setError(false)
    try {
      const res = await api.procrastinationForTask(token, taskId)
      setD(res)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  const style = d ? (TRIGGER_STYLE[d.trigger] || TRIGGER_STYLE.ambiguity) : null

  return (
    <div className="mt-3 pt-3 border-t border-navy/5">
      <button
        onClick={analyze}
        className="text-[11px] font-body text-night-blue/70 hover:text-night-blue transition-colors flex items-center gap-1.5"
      >
        <span>🧭</span>
        {open ? 'Hide insight' : 'Why am I avoiding this?'}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3">
              {loading ? (
                <div className="flex items-center gap-2 text-navy/40 text-[12px] font-body py-2">
                  <div className="w-3 h-3 rounded-full border border-night-blue/30 border-t-night-blue animate-spin" />
                  Gemini is reading the pattern…
                </div>
              ) : error ? (
                <p className="text-[12px] text-coral/80 font-body py-1">Couldn’t analyze right now — try again in a moment.</p>
              ) : d ? (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="skill-badge"
                      style={{ background: style!.bg, color: style!.fg }}
                    >
                      {style!.emoji} {d.trigger}
                    </span>
                    <span className="text-[11px] text-navy/40 font-body">the likely root</span>
                  </div>
                  <p className="text-[12.5px] text-navy/70 font-body font-light leading-relaxed">
                    {d.trigger_explanation}
                  </p>
                  <div className="rounded-xl bg-night-blue/[0.04] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-navy/35 font-body mb-1">Try this</p>
                    <p className="text-[12.5px] text-navy/75 font-body leading-relaxed">{d.intervention}</p>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-xl p-3" style={{ background: '#E3F1E8' }}>
                    <div>
                      <p className="text-[10px] uppercase tracking-widest font-body mb-0.5 font-semibold" style={{ color: '#2F6B47' }}>
                        First step · {d.estimated_start_minutes ?? 5} min
                      </p>
                      <p className="text-[12.5px] font-body leading-snug" style={{ color: '#26324A' }}>{d.first_step}</p>
                    </div>
                    <button
                      onClick={onStartFirstStep}
                      className="flex-shrink-0 text-[11px] font-medium text-white px-3 py-1.5 rounded-xl font-body transition-transform hover:-translate-y-0.5"
                      style={{ background: 'linear-gradient(135deg, #7EBF95 0%, #6BAE84 100%)' }}
                    >
                      Start →
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
