'use client'
import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Task, RescheduleOptions, RescheduleWindow } from '@/lib/types'

interface Props {
  task: Task | null
  open: boolean
  onClose: () => void
  onDone: () => void
}

const REASONS = [
  { key: 'low_energy', label: 'Low energy' },
  { key: 'blocked_externally', label: 'Blocked by someone' },
  { key: 'ambiguity', label: 'Unclear what to do' },
  { key: 'no_longer_needed', label: 'May not be needed' },
]

function energyColor(s: number) {
  return s >= 0.85 ? '#7EBF95' : s >= 0.65 ? '#6D8FD8' : '#B8A9D4'
}

function dayLabel(iso: string) {
  const d = new Date(iso)
  const today = new Date()
  const tomorrow = new Date(); tomorrow.setDate(today.getDate() + 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return d.toLocaleDateString('en-US', { weekday: 'long' })
}

export default function RescheduleModal({ task, open, onClose, onDone }: Props) {
  const { token } = useAuth()
  const [opts, setOpts] = useState<RescheduleOptions | null>(null)
  const [loading, setLoading] = useState(false)
  const [reason, setReason] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)
  const [needReasonError, setNeedReasonError] = useState(false)

  const load = useCallback(async () => {
    if (!token || !task) return
    setLoading(true); setOpts(null); setReason(null); setNeedReasonError(false)
    try {
      setOpts(await api.getRescheduleOptions(token, task.id))
    } catch {
      setOpts(null)
    } finally {
      setLoading(false)
    }
  }, [token, task])

  useEffect(() => { if (open && task) load() }, [open, task, load])

  const apply = async (w: RescheduleWindow) => {
    if (!token || !task || applying) return
    if (opts?.requires_reason && !reason) { setNeedReasonError(true); return }
    setApplying(true)
    try {
      await api.rescheduleTask(token, task.id, w.start, reason ?? undefined)
      onDone()
      onClose()
    } catch {
      // keep modal open on error
    } finally {
      setApplying(false)
    }
  }

  return (
    <AnimatePresence>
      {open && task && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'rgba(6, 9, 20, 0.94)', backdropFilter: 'blur(10px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="modal-panel w-full max-w-lg p-7 relative max-h-[88vh] overflow-y-auto"
          >
            <div className="flex items-start justify-between mb-5">
              <div className="pr-4">
                <h2 className="text-xl font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
                  Reschedule
                </h2>
                <p className="text-navy/45 text-[13px] font-body mt-0.5 line-clamp-1">{task.title}</p>
                {task.reschedule_count > 0 && (
                  <p className="text-[11px] text-amber-600 font-body mt-1">
                    ↺ Moved {task.reschedule_count} time{task.reschedule_count === 1 ? '' : 's'} already
                  </p>
                )}
              </div>
              <button onClick={onClose} className="w-8 h-8 rounded-full bg-navy/5 hover:bg-navy/10 flex items-center justify-center text-navy/40">✕</button>
            </div>

            {loading ? (
              <div className="flex flex-col items-center py-12 gap-3">
                <div className="w-8 h-8 rounded-full border-2 border-night-blue/20 border-t-night-blue animate-spin" />
                <p className="text-navy/40 text-sm font-body">Finding viable windows…</p>
              </div>
            ) : !opts ? (
              <p className="text-coral/80 text-sm font-body py-8 text-center">Couldn’t load options. Try again.</p>
            ) : opts.no_options ? (
              <div>
                <div className="flex items-center gap-2 mb-3 text-amber-700">
                  <span>⚠️</span>
                  <span className="text-sm font-medium font-body">No viable windows before your deadline</span>
                </div>
                <p className="text-navy/55 text-[13px] font-body mb-4">When there’s no room left, the move isn’t the answer. Consider:</p>
                <div className="space-y-2">
                  {opts.no_options_alternatives.map((alt, i) => (
                    <div key={i} className="flex items-start gap-2 rounded-xl bg-night-blue/[0.04] p-3">
                      <span className="text-night-blue text-xs mt-0.5">{i + 1}</span>
                      <span className="text-[13px] text-navy/70 font-body">{alt}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <p className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body mb-3">
                  {opts.windows.length} viable window{opts.windows.length === 1 ? '' : 's'}
                </p>

                {opts.requires_reason && (
                  <div className="mb-4">
                    <p className="text-[13px] text-navy/60 font-body mb-2">
                      You’ve moved this a few times — what’s getting in the way?
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {REASONS.map(r => (
                        <button
                          key={r.key}
                          onClick={() => { setReason(r.key); setNeedReasonError(false) }}
                          className={`text-[12px] font-body px-3 py-1.5 rounded-full transition-all ${reason === r.key ? 'text-white' : 'text-navy/55 glass-card'}`}
                          style={reason === r.key ? { background: 'linear-gradient(135deg,#6D8FD8,#8BA5E0)' } : {}}
                        >
                          {r.label}
                        </button>
                      ))}
                    </div>
                    {needReasonError && (
                      <p className="text-[11px] text-coral mt-1.5 font-body">Pick a reason to continue.</p>
                    )}
                  </div>
                )}

                <div className="space-y-3">
                  {opts.windows.map((w, i) => (
                    <button
                      key={i}
                      onClick={() => apply(w)}
                      disabled={applying}
                      className="w-full text-left glass-card p-4 hover:-translate-y-0.5 transition-transform disabled:opacity-60"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <span className="text-[15px] font-medium text-navy font-body">{dayLabel(w.start)}</span>
                          <span className="text-[13px] text-navy/50 font-body ml-2">
                            {new Date(w.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                          </span>
                        </div>
                        <span className="skill-badge" style={{ color: '#5BB082' }}>
                          {w.label} energy
                        </span>
                      </div>
                      <div className="h-1.5 bg-navy/6 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${w.energy_score * 100}%`, background: energyColor(w.energy_score) }} />
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-[11px] text-navy/40 font-body">
                        {w.tasks_displaced > 0 && <span>↔ displaces {w.tasks_displaced}</span>}
                        {w.cascade_impact > 0 && <span>🌊 affects {w.cascade_impact} downstream</span>}
                        {w.tasks_displaced === 0 && w.cascade_impact === 0 && <span>No conflicts</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
