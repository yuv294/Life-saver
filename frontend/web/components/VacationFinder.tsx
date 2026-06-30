'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface Win {
  start: string
  end: string
  duration_days: number
  blast_radius: number
  tasks_at_risk?: string[]
  recommendation?: string
}

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function VacationFinder() {
  const { token } = useAuth()
  const [windows, setWindows] = useState<Win[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api.getVacationFinder(token)
      .then(r => { setWindows(r.windows ?? []); setMessage(r.message ?? null) })
      .catch(() => setWindows([]))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-base">🌴</span>
        <div>
          <h3 className="text-[15px] font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
            Breathing room
          </h3>
          <p className="text-[11px] text-navy/40 font-body mt-0.5">Low-pressure windows to step away</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-6">
          <div className="w-6 h-6 rounded-full border-2 border-night-blue/20 border-t-night-blue animate-spin" />
        </div>
      ) : windows.length === 0 ? (
        <p className="text-navy/35 text-sm font-body text-center py-6">
          {message || 'No clear windows in the next 90 days.'}
        </p>
      ) : (
        <div className="space-y-3">
          {windows.map((w, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="rounded-xl p-3"
              style={{ background: w.blast_radius === 0 ? '#E3F1E8' : '#FBEFD6' }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[14px] font-semibold font-body" style={{ color: '#26324A' }}>
                  {fmt(w.start)} – {fmt(w.end)}
                </span>
                <span className="text-[11px] font-body" style={{ color: '#5A6075' }}>{w.duration_days} day{w.duration_days === 1 ? '' : 's'}</span>
              </div>
              <p className="text-[12px] font-body" style={{ color: '#3A4258' }}>{w.recommendation}</p>
              {w.tasks_at_risk && w.tasks_at_risk.length > 0 && (
                <p className="text-[11px] font-body mt-1" style={{ color: '#8A5A00' }}>
                  Waiting after: {w.tasks_at_risk.join(', ')}
                </p>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
