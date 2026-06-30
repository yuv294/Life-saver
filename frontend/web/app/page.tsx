'use client'
import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Nav from '@/components/Nav'
import AuthGate from '@/components/AuthGate'
import DailyBrief from '@/components/DailyBrief'
import TaskCard from '@/components/TaskCard'
import CreateTaskModal from '@/components/CreateTaskModal'
import MomentumMeter from '@/components/MomentumMeter'
import SkillClusters from '@/components/SkillClusters'
import EnergyNow from '@/components/EnergyNow'
import RecoveryMode from '@/components/RecoveryMode'
import OverdueRecovery from '@/components/OverdueRecovery'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Task } from '@/lib/types'

function stagger(i: number) {
  return { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] } }
}

export default function Home() {
  const { token } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [nextSession, setNextSession] = useState<any>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [recovery, setRecovery] = useState(false)

  useEffect(() => {
    setRecovery(localStorage.getItem('ls-recovery') === 'on')
  }, [])
  const setRecoveryMode = (on: boolean) => {
    setRecovery(on)
    localStorage.setItem('ls-recovery', on ? 'on' : 'off')
  }

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const [t, ns] = await Promise.allSettled([
        api.getTasks(token),
        api.getNextSession(token),
      ])
      if (t.status === 'fulfilled') setTasks(t.value)
      if (ns.status === 'fulfilled') setNextSession(ns.value)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const pending = tasks.filter(t => t.status !== 'completed' && t.status !== 'abandoned')
  const done = tasks.filter(t => t.status === 'completed')
  const momentum = tasks.length === 0 ? 0 : Math.round((done.length / tasks.length) * 100)

  const doFirst = pending.filter(t => t.eisenhower_quadrant === 1).slice(0, 3)
  const rest = pending.filter(t => t.eisenhower_quadrant !== 1).slice(0, 4)

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <div className="min-h-screen">
      <Nav />
      <AuthGate>
        {recovery ? (
          <RecoveryMode tasks={tasks} onExit={() => setRecoveryMode(false)} onUpdate={load} />
        ) : (
        <>
        <main className="max-w-5xl mx-auto px-6 pb-20">
          {/* Hero line */}
          <motion.div {...stagger(0)} className="mb-8 mt-6">
            <div className="flex items-center justify-between gap-3">
              <button
                onClick={() => setRecoveryMode(true)}
                className="text-xs font-body px-3 py-1.5 rounded-full glass-card transition-transform hover:-translate-y-0.5"
                style={{ color: 'var(--text-muted)' }}
                title="Feeling overwhelmed? Switch to a calm, one-task view"
              >
                🌙 Recovery mode
              </button>
            </div>
            <div className="flex items-baseline gap-3">
              <h1
                className="text-5xl font-bold text-navy leading-none"
                style={{ fontFamily: 'Fraunces, serif' }}
              >
                Today's
              </h1>
              <span
                className="text-5xl font-light italic text-night-blue leading-none"
                style={{ fontFamily: 'Fraunces, serif' }}
              >
                little wins
              </span>
            </div>
            <p className="text-navy/40 text-sm font-body mt-2 font-light">{today}</p>
          </motion.div>

          {/* Main grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Left column — brief + tasks */}
            <div className="lg:col-span-2 flex flex-col gap-5">
              <motion.div {...stagger(1)}>
                <DailyBrief />
              </motion.div>

              <motion.div {...stagger(2)}>
                <EnergyNow />
              </motion.div>

              <motion.div {...stagger(2)}>
                <OverdueRecovery />
              </motion.div>

              {/* Next focus session */}
              {nextSession && nextSession.cluster && (
                <motion.div {...stagger(2)} className="glass-card p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base">⭐</span>
                    <span className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">Best next session</span>
                  </div>
                  <p className="text-navy font-medium font-body text-[15px]">
                    Work on <span className="text-night-blue">{nextSession.cluster.name}</span> — {nextSession.cluster.task_ids?.length || 0} task{(nextSession.cluster.task_ids?.length || 0) === 1 ? '' : 's'} ready
                  </p>
                  <p className="text-navy/45 text-sm font-body font-light mt-1">
                    ~{Math.round(nextSession.cluster.estimated_total_hours || 0)}h · {nextSession.cluster.dominant_skill} focus
                  </p>
                </motion.div>
              )}

              {/* Skill cluster cards */}
              <motion.div {...stagger(3)}>
                <SkillClusters />
              </motion.div>

              {/* Do-first tasks */}
              {doFirst.length > 0 && (
                <div>
                  <motion.div {...stagger(3)} className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-sage" style={{ boxShadow: '0 0 6px rgba(126,191,149,0.6)' }} />
                    <span className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">Start here</span>
                  </motion.div>
                  <div className="flex flex-col gap-3">
                    {doFirst.map((t, i) => (
                      <motion.div key={t.id} {...stagger(4 + i)}>
                        <TaskCard task={t} onUpdate={load} />
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Other pending */}
              {rest.length > 0 && (
                <div>
                  <motion.div {...stagger(7)} className="flex items-center gap-2 mb-3">
                    <div className="constellation-dot" style={{ width: 5, height: 5 }} />
                    <span className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">In orbit</span>
                  </motion.div>
                  <div className="flex flex-col gap-3">
                    {rest.map((t, i) => (
                      <motion.div key={t.id} {...stagger(8 + i)}>
                        <TaskCard task={t} onUpdate={load} compact />
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {pending.length === 0 && !loading && (
                <motion.div {...stagger(2)} className="glass-card p-10 text-center">
                  <div className="text-4xl mb-3">✨</div>
                  <h3 className="text-lg font-bold text-navy mb-1" style={{ fontFamily: 'Fraunces, serif' }}>
                    Sky is clear
                  </h3>
                  <p className="text-navy/45 text-sm font-body font-light">Add your first task below</p>
                </motion.div>
              )}
            </div>

            {/* Right column */}
            <div className="flex flex-col gap-5">
              <motion.div {...stagger(2)}>
                <MomentumMeter value={momentum} />
              </motion.div>

              {/* Stats card */}
              <motion.div {...stagger(3)} className="glass-card p-5">
                <div className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body mb-4">Overview</div>
                {[
                  { label: 'Pending', value: pending.length, color: '#6D8FD8' },
                  { label: 'Completed', value: done.length, color: '#7EBF95' },
                  { label: 'Total', value: tasks.length, color: '#B8A9D4' },
                ].map(s => (
                  <div key={s.label} className="flex items-center justify-between py-2.5 border-b border-navy/5 last:border-0">
                    <span className="text-sm text-navy/60 font-body">{s.label}</span>
                    <span className="font-bold text-navy font-body" style={{ color: s.color }}>{s.value}</span>
                  </div>
                ))}
              </motion.div>

              {/* Moon phase decoration */}
              <motion.div
                {...stagger(4)}
                className="glass-card p-5 text-center"
                style={{ animation: 'float 10s ease-in-out infinite 1s' }}
              >
                <div className="text-5xl mb-2" style={{ filter: 'drop-shadow(0 0 12px rgba(245,201,106,0.4))' }}>🌙</div>
                <p className="text-navy/35 text-xs font-body font-light leading-relaxed">
                  You don't have to do<br />everything. Just the<br />next small thing.
                </p>
              </motion.div>
            </div>
          </div>
        </main>

        {/* FAB */}
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.6, type: 'spring', stiffness: 260, damping: 20 }}
          whileHover={{ scale: 1.08, y: -2 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setCreateOpen(true)}
          className="fixed bottom-8 right-8 w-14 h-14 rounded-full text-white text-xl flex items-center justify-center z-20 animate-glow-pulse"
          style={{
            background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)',
            boxShadow: '0 6px 24px rgba(109, 143, 216, 0.45)',
          }}
          title="Add task"
        >
          +
        </motion.button>

        <CreateTaskModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreated={load}
        />
        </>
        )}
      </AuthGate>
    </div>
  )
}
