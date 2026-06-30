'use client'
import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Nav from '@/components/Nav'
import AuthGate from '@/components/AuthGate'
import ConstellationMap from '@/components/ConstellationMap'
import VacationFinder from '@/components/VacationFinder'
import SkillLevels from '@/components/SkillLevels'
import HabitTracker from '@/components/HabitTracker'
import PlanningAccuracyCard from '@/components/PlanningAccuracyCard'
import RecoveryShield from '@/components/RecoveryShield'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Task } from '@/lib/types'

function EnergyBar({ level, label, time }: { level: number; label: string; time: string }) {
  const color = level >= 0.7 ? '#7EBF95' : level >= 0.4 ? '#6D8FD8' : '#B8A9D4'
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-navy/40 font-body w-14 flex-shrink-0">{time}</span>
      <div className="flex-1 h-2 bg-navy/6 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}60` }}
          initial={{ width: 0 }}
          animate={{ width: `${level * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
        />
      </div>
      <span className="text-[11px] text-navy/50 font-body w-16 flex-shrink-0">{label}</span>
    </div>
  )
}

export default function JourneyPage() {
  const { token } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [energyWindows, setEnergyWindows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const [t, e] = await Promise.allSettled([
        api.getTasks(token),
        api.getEnergyWindows(token),
      ])
      if (t.status === 'fulfilled') setTasks(t.value)
      if (e.status === 'fulfilled') {
        const w = (e.value as any)?.windows ?? e.value ?? []
        setEnergyWindows(Array.isArray(w) ? w.slice(0, 16) : [])
      }
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const doneTasks = tasks.filter(t => t.status === 'completed')
  const wins = doneTasks.slice(0, 12)

  return (
    <div className="min-h-screen">
      <Nav />
      <AuthGate>
        <main className="max-w-5xl mx-auto px-6 pb-24">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
            className="mt-6 mb-8"
          >
            <h1 className="text-4xl font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
              Your journey
            </h1>
            <p className="text-navy/40 text-sm font-body mt-1 font-light">
              Every completed task is a star in your sky
            </p>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* 21/90 habit tracker — full width */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="lg:col-span-3"
            >
              <HabitTracker />
            </motion.div>

            {/* Constellation */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.55 }}
              className="lg:col-span-2"
            >
              <ConstellationMap tasks={tasks} width={580} height={380} />
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.55 }}
              className="glass-card p-6"
            >
              <div className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body mb-5">Numbers</div>
              {[
                { label: 'Wins (done)', value: doneTasks.length, icon: '✦', color: '#F5C96A' },
                { label: 'In motion', value: tasks.filter(t => t.status !== 'completed' && t.status !== 'abandoned').length, icon: '○', color: '#6D8FD8' },
                { label: 'Skill areas', value: new Set(tasks.flatMap(t => t.skill_tags || [])).size, icon: '◈', color: '#7EBF95' },
              ].map(s => (
                <div key={s.label} className="flex items-center justify-between py-3 border-b border-navy/5 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm" style={{ color: s.color }}>{s.icon}</span>
                    <span className="text-sm text-navy/60 font-body">{s.label}</span>
                  </div>
                  <span className="text-xl font-bold font-body" style={{ fontFamily: 'Fraunces, serif', color: s.color }}>
                    {s.value}
                  </span>
                </div>
              ))}

              {/* Progress bar */}
              {tasks.length > 0 && (
                <div className="mt-5">
                  <div className="flex justify-between text-[11px] text-navy/35 font-body mb-1.5">
                    <span>Completion</span>
                    <span>{Math.round((doneTasks.length / tasks.length) * 100)}%</span>
                  </div>
                  <div className="h-2 bg-navy/6 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: 'linear-gradient(90deg, #6D8FD8, #7EBF95)' }}
                      initial={{ width: 0 }}
                      animate={{ width: `${(doneTasks.length / tasks.length) * 100}%` }}
                      transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
                    />
                  </div>
                </div>
              )}
            </motion.div>

            {/* Energy windows */}
            {energyWindows.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.55 }}
                className="lg:col-span-2 glass-card p-6"
              >
                <div className="flex items-center gap-2 mb-5">
                  <span className="text-base">⚡</span>
                  <div>
                    <h3 className="text-[15px] font-bold text-navy font-display" style={{ fontFamily: 'Fraunces, serif' }}>
                      Energy forecast
                    </h3>
                    <p className="text-[11px] text-navy/40 font-body mt-0.5">Next 8 hours based on your patterns</p>
                  </div>
                </div>
                <div className="space-y-2">
                  {energyWindows.slice(0, 8).map((w: any, i: number) => (
                    <EnergyBar
                      key={i}
                      level={w.energy_score ?? w.level ?? 0.5}
                      label={w.label ?? w.recommended_complexity ?? ''}
                      time={w.start ? new Date(w.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
                    />
                  ))}
                </div>
              </motion.div>
            )}

            {/* Wins wall */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.55 }}
              className={energyWindows.length > 0 ? '' : 'lg:col-span-2'}
            >
              <div className="glass-card p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-base">🌟</span>
                  <h3 className="text-[15px] font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
                    Wins wall
                  </h3>
                </div>
                {wins.length === 0 ? (
                  <p className="text-navy/35 text-sm font-body text-center py-6">
                    Complete tasks to see them light up here
                  </p>
                ) : (
                  <div className="space-y-2">
                    {wins.map((t, i) => (
                      <motion.div
                        key={t.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 + 0.5 }}
                        className="flex items-center gap-2.5 py-2 border-b border-navy/5 last:border-0"
                      >
                        <span className="text-amber text-sm">✦</span>
                        <span className="text-[13px] text-navy/70 font-body line-clamp-1">{t.title}</span>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>

            {/* Skill levels */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45, duration: 0.55 }}
            >
              <SkillLevels tasks={tasks} />
            </motion.div>

            {/* Planning accuracy */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.55 }}
            >
              <PlanningAccuracyCard />
            </motion.div>

            {/* Recovery shields */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55, duration: 0.55 }}
            >
              <RecoveryShield />
            </motion.div>

            {/* Vacation finder */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.55 }}
              className="lg:col-span-2"
            >
              <VacationFinder />
            </motion.div>
          </div>
        </main>
      </AuthGate>
    </div>
  )
}
