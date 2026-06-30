'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { skillColor } from '@/lib/types'

interface Summary {
  overall_inflation: number | null
  sample_count: number
  per_skill: Record<string, { inflation: number; count: number }>
}

export default function PlanningAccuracyCard() {
  const { token } = useAuth()
  const [s, setS] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api.getPlanningSummary(token).then(setS).catch(() => setS(null)).finally(() => setLoading(false))
  }, [token])

  const skills = s ? Object.entries(s.per_skill).sort((a, b) => b[1].count - a[1].count) : []

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-base">📐</span>
        <div>
          <h3 className="text-[15px] font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
            Planning accuracy
          </h3>
          <p className="text-[11px] text-navy/40 font-body mt-0.5">Estimate vs. reality</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><div className="w-6 h-6 rounded-full border-2 border-night-blue/20 border-t-night-blue animate-spin" /></div>
      ) : !s || s.overall_inflation == null ? (
        <p className="text-navy/35 text-sm font-body text-center py-6">
          Complete a few tasks with real time logged to learn your pace.
        </p>
      ) : (
        <>
          <div className="text-center mb-4">
            <div className="text-3xl font-bold" style={{ fontFamily: 'Fraunces, serif', color: s.overall_inflation > 1.1 ? '#E08A76' : '#7EBF95' }}>
              {s.overall_inflation}×
            </div>
            <p className="text-[12px] text-navy/45 font-body">
              your tasks take {s.overall_inflation > 1 ? 'longer' : 'less'} than planned ({s.sample_count} completed)
            </p>
          </div>
          <div className="space-y-2">
            {skills.map(([skill, v], i) => {
              const col = skillColor(skill)
              const w = Math.min(100, (v.inflation / 3) * 100)
              return (
                <motion.div key={skill} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.05 }}>
                  <div className="flex justify-between text-[11px] font-body mb-0.5">
                    <span className="text-navy/55 capitalize">{skill}</span>
                    <span className="text-navy/45">{v.inflation}× · {v.count}×done</span>
                  </div>
                  <div className="h-1.5 bg-navy/6 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${w}%`, background: col.fg }} />
                  </div>
                </motion.div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
