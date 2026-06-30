'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { EnergyWindow } from '@/lib/types'

const COLOR: Record<string, string> = { peak: '#7EBF95', high: '#6D8FD8', medium: '#F5C96A', low: '#B8A9D4' }
const FIT: Record<string, string> = {
  peak: 'Prime time for your hardest, most analytical work.',
  high: 'Good window for focused, meaningful tasks.',
  medium: 'Better for admin, email, and lighter tasks.',
  low: 'Energy dips here — a fine time to rest or do something easy.',
}

function fmt(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export default function EnergyNow() {
  const { token } = useAuth()
  const [now, setNow] = useState<EnergyWindow | null>(null)
  const [microBreak, setMicroBreak] = useState<EnergyWindow | null>(null)

  useEffect(() => {
    if (!token) return
    api.getEnergyWindows(token).then(r => {
      const w = r.windows || []
      const t = Date.now()
      const cur = w.find(x => new Date(x.start).getTime() <= t && t < new Date(x.end).getTime()) || w[0] || null
      setNow(cur)
      // micro-break: lowest-energy future window left today
      const today = new Date().toDateString()
      const future = w.filter(x => new Date(x.start).getTime() > t && new Date(x.start).toDateString() === today)
      const dip = future.slice().sort((a, b) => a.energy_score - b.energy_score)[0]
      setMicroBreak(dip && dip.energy_score < 0.55 ? dip : null)
    }).catch(() => {})
  }, [token])

  if (!now) return null
  const col = COLOR[now.label] || '#6D8FD8'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4 flex items-center gap-3"
    >
      <div className="relative flex-shrink-0">
        <motion.div
          animate={{ scale: [1, 1.25, 1], opacity: [0.6, 0.2, 0.6] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute inset-0 rounded-full" style={{ background: col }}
        />
        <div className="relative w-3 h-3 rounded-full" style={{ background: col, boxShadow: `0 0 8px ${col}` }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-navy font-body">
          <span style={{ color: col }} className="capitalize">{now.label} energy</span> right now
        </p>
        <p className="text-[12px] text-navy/50 font-body leading-snug">{FIT[now.label]}</p>
        {microBreak && (
          <p className="text-[11px] text-navy/40 font-body mt-1">
            ☕ Good micro-break around <b>{fmt(microBreak.start)}</b> (energy dips)
          </p>
        )}
      </div>
    </motion.div>
  )
}
