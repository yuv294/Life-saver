'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export default function StreakFlame() {
  const { token } = useAuth()
  const [streak, setStreak] = useState<number>(0)
  const [recovery, setRecovery] = useState<number>(0)

  useEffect(() => {
    if (!token) return
    api.getStreak(token)
      .then(s => { setStreak(s.streak_count ?? 0); setRecovery(s.recovery_days_remaining ?? 0) })
      .catch(() => {})
  }, [token])

  if (streak <= 0) return null

  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      className="flex items-center gap-1 card px-2.5 py-1.5 rounded-full"
      title={`${streak}-day streak · ${recovery} recovery day${recovery === 1 ? '' : 's'} left`}
    >
      <motion.span
        animate={{ scale: [1, 1.18, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        style={{ fontSize: 14 }}
      >
        🔥
      </motion.span>
      <span className="text-sm font-bold" style={{ color: 'var(--amber)' }}>{streak}</span>
    </motion.div>
  )
}
