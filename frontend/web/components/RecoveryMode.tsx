'use client'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Task, isActive } from '@/lib/types'

/** Pick the gentlest next action: an in-progress task, else the smallest do-first, else smallest. */
function pickOne(tasks: Task[]): Task | null {
  const active = tasks.filter(isActive)
  if (active.length === 0) return null
  const inProg = active.filter(t => t.status === 'in_progress')
  const pool = inProg.length ? inProg : active
  return pool.slice().sort((a, b) =>
    (a.eisenhower_quadrant === 1 ? -1 : 0) - (b.eisenhower_quadrant === 1 ? -1 : 0)
    || (a.estimated_hours || 99) - (b.estimated_hours || 99)
  )[0]
}

export default function RecoveryMode({ tasks, onExit, onUpdate }: { tasks: Task[]; onExit: () => void; onUpdate: () => void }) {
  const { token } = useAuth()
  const [done, setDone] = useState(false)
  const task = pickOne(tasks)

  const complete = async () => {
    if (!token || !task) return
    try { await api.completeTask(token, task.id); setDone(true); onUpdate() } catch {}
  }

  return (
    <div className="min-h-[78vh] flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md text-center"
      >
        <motion.div
          animate={{ scale: [1, 1.06, 1] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
          className="text-5xl mb-6" style={{ filter: 'drop-shadow(0 0 20px rgba(184,169,212,0.5))' }}
        >
          🌙
        </motion.div>
        <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: 'Fraunces, serif', color: 'var(--text)' }}>
          Recovery mode
        </h1>
        <p className="text-sm font-body mb-8" style={{ color: 'var(--text-muted)' }}>
          No lists. No pressure. Just one gentle thing — or nothing at all.
        </p>

        {done || !task ? (
          <div className="card p-10" style={{ background: 'linear-gradient(135deg, rgba(126,191,149,0.12), rgba(184,169,212,0.12))' }}>
            <div className="text-4xl mb-3">{done ? '✨' : '🫧'}</div>
            <p className="text-lg font-body" style={{ color: 'var(--text)' }}>
              {done ? "That's enough. Be proud of that." : "Nothing needs you right now. Rest."}
            </p>
          </div>
        ) : (
          <motion.div
            className="card p-8"
            style={{ background: 'linear-gradient(135deg, rgba(126,191,149,0.10), rgba(184,169,212,0.10))' }}
          >
            <p className="text-[11px] uppercase tracking-widest font-body mb-3" style={{ color: 'var(--text-faint)' }}>
              The one thing
            </p>
            <p className="text-xl font-medium font-body mb-1" style={{ color: 'var(--text)' }}>{task.title}</p>
            {task.estimated_hours ? (
              <p className="text-sm font-body mb-6" style={{ color: 'var(--text-muted)' }}>
                ~{task.estimated_hours}h · take it slow
              </p>
            ) : <div className="mb-6" />}
            <button
              onClick={complete}
              className="w-full py-3 rounded-2xl text-white text-sm font-medium font-body transition-transform hover:-translate-y-0.5"
              style={{ background: 'linear-gradient(135deg,#7EBF95,#6BAE84)' }}
            >
              I did this one ✓
            </button>
          </motion.div>
        )}

        <button onClick={onExit} className="mt-8 text-sm font-body transition-colors" style={{ color: 'var(--text-muted)' }}>
          ← Back to full view
        </button>
      </motion.div>
    </div>
  )
}
