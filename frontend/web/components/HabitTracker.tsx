'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

const MILESTONES = [7, 14, 21, 30, 60, 90]
const LABELS: Record<number, string> = { 7: 'Spark', 14: 'Rhythm', 21: 'Habit', 30: 'Locked in', 60: 'Second nature', 90: 'Mastery' }

export default function HabitTracker() {
  const { token } = useAuth()
  const [streak, setStreak] = useState(0)

  useEffect(() => {
    if (!token) return
    api.getStreak(token).then(s => setStreak(s.streak_count ?? 0)).catch(() => {})
  }, [token])

  const max = MILESTONES[MILESTONES.length - 1]
  const pct = Math.min(100, (streak / max) * 100)
  const next = MILESTONES.find(m => m > streak)
  const graduated = streak >= max

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <span className="text-base">{graduated ? '🌟' : '🌱'}</span>
          <h3 className="text-[15px] font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
            {graduated ? 'Journey complete' : '21 / 90 journey'}
          </h3>
        </div>
        <span className="text-[12px] text-navy/45 font-body">
          {graduated ? '✨ 90 days' : `${streak} day${streak === 1 ? '' : 's'}${next ? ` · ${next - streak} to ${LABELS[next]}` : ''}`}
        </span>
      </div>

      {graduated && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="rounded-2xl p-5 mb-5 text-center"
          style={{ background: 'linear-gradient(135deg, rgba(126,191,149,0.18), rgba(245,201,106,0.18))', border: '1px solid rgba(126,191,149,0.35)' }}
        >
          <div className="text-3xl mb-2">🎉</div>
          <p className="text-[15px] font-bold text-navy font-body mb-1" style={{ fontFamily: 'Fraunces, serif' }}>
            You made it — 90 days.
          </p>
          <p className="text-[12.5px] text-navy/60 font-body leading-relaxed">
            This isn't a streak anymore — it's who you are now. We'll stop the counter here;
            the habit is yours to keep. 🌿
          </p>
        </motion.div>
      )}

      <div className="relative h-2 bg-navy/6 rounded-full mb-6">
        <motion.div
          className="absolute left-0 top-0 h-full rounded-full"
          style={{ background: 'linear-gradient(90deg,#7EBF95,#6D8FD8)' }}
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
        {MILESTONES.map(m => {
          const reached = streak >= m
          return (
            <div key={m} className="absolute -translate-x-1/2" style={{ left: `${(m / max) * 100}%`, top: '50%' }}>
              <div className="-translate-y-1/2 rounded-full border-2"
                style={{
                  width: 12, height: 12,
                  background: reached ? '#7EBF95' : 'var(--surface, #fff)',
                  borderColor: reached ? '#7EBF95' : 'rgba(26,31,53,0.15)',
                  boxShadow: reached ? '0 0 8px rgba(126,191,149,0.6)' : 'none',
                }} />
              <span className="absolute top-3 left-1/2 -translate-x-1/2 text-[9px] text-navy/40 font-body">{m}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
