'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

const TOTAL = 4

export default function RecoveryShield() {
  const { token } = useAuth()
  const [remaining, setRemaining] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [justUsed, setJustUsed] = useState(false)

  useEffect(() => {
    if (!token) return
    api.getStreak(token).then(s => setRemaining(s.recovery_days_remaining ?? TOTAL)).catch(() => {})
  }, [token])

  const use = async () => {
    if (!token || busy || (remaining ?? 0) <= 0) return
    setBusy(true)
    try {
      const r = await api.declareRecoveryDay(token)
      setRemaining(r.days_remaining ?? Math.max(0, (remaining ?? 1) - 1))
      setJustUsed(true)
      setTimeout(() => setJustUsed(false), 2500)
    } catch {} finally { setBusy(false) }
  }

  if (remaining == null) return null

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">🛡️</span>
        <h3 className="text-[14px] font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>Recovery shields</h3>
      </div>
      <div className="flex items-center gap-1.5 mb-3">
        {Array.from({ length: TOTAL }).map((_, i) => (
          <motion.span key={i} initial={false} animate={{ scale: i < remaining ? 1 : 0.85, opacity: i < remaining ? 1 : 0.3 }}
            style={{ fontSize: 18, filter: i < remaining ? 'none' : 'grayscale(1)' }}>
            🛡️
          </motion.span>
        ))}
        <span className="text-[12px] text-navy/45 font-body ml-1">{remaining}/{TOTAL} left this month</span>
      </div>
      <p className="text-[11px] text-navy/45 font-body mb-3 leading-relaxed">
        Life happens. Use a shield to protect your streak on a day you can't show up.
      </p>
      <button
        onClick={use}
        disabled={busy || remaining <= 0}
        className="text-[12px] font-medium text-white px-3 py-1.5 rounded-xl font-body transition-transform hover:-translate-y-0.5 disabled:opacity-50"
        style={{ background: 'linear-gradient(135deg,#B8A9D4,#9F8EC4)' }}
      >
        {justUsed ? '✓ Streak protected' : busy ? '…' : remaining <= 0 ? 'None left' : 'Use a recovery day'}
      </button>
    </div>
  )
}
