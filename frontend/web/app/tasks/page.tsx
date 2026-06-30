'use client'
import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Nav from '@/components/Nav'
import AuthGate from '@/components/AuthGate'
import TaskCard from '@/components/TaskCard'
import CreateTaskModal from '@/components/CreateTaskModal'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Task } from '@/lib/types'

type Filter = 'all' | 'pending' | 'completed' | 'do_first' | 'schedule'

export default function TasksPage() {
  const { token } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [filter, setFilter] = useState<Filter>('pending')
  const [createOpen, setCreateOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [auditResult, setAuditResult] = useState<any>(null)
  const [auditLoading, setAuditLoading] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const t = await api.getTasks(token)
      setTasks(t)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const filtered = tasks.filter(t => {
    if (filter === 'all') return true
    if (filter === 'pending') return t.status === 'pending' || t.status === 'in_progress'
    if (filter === 'completed') return t.status === 'completed'
    if (filter === 'do_first') return t.eisenhower_quadrant === 1
    if (filter === 'schedule') return t.eisenhower_quadrant === 2
    return true
  })

  // Group by dominant skill tag
  const byCluster = new Map<string, Task[]>()
  for (const t of filtered) {
    const key = (t.skill_tags && t.skill_tags[0]) || 'general'
    if (!byCluster.has(key)) byCluster.set(key, [])
    byCluster.get(key)!.push(t)
  }

  const runAudit = async () => {
    if (!token) return
    setAuditLoading(true)
    try {
      const r = await api.runBacklogAudit(token)
      setAuditResult(r)
    } finally {
      setAuditLoading(false)
    }
  }

  const applyAudit = async (taskId: string, action: 'abandon' | 'delegate' | 'defer') => {
    if (!token) return
    try {
      if (action === 'defer') {
        const d = new Date(Date.now() + 14 * 86400000).toISOString()
        await api.updateTask(token, taskId, { deadline: d })
      } else {
        // abandon + delegate both leave the active backlog
        await api.updateTask(token, taskId, { status: 'abandoned' })
      }
      // drop the handled candidate from the panel + refresh list
      setAuditResult((r: any) => r ? { ...r, candidates: r.candidates.filter((c: any) => c.task_id !== taskId) } : r)
      load()
    } catch {}
  }

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'pending', label: 'Active' },
    { key: 'do_first', label: 'Do First' },
    { key: 'schedule', label: 'Schedule' },
    { key: 'completed', label: 'Done' },
    { key: 'all', label: 'All' },
  ]

  return (
    <div className="min-h-screen">
      <Nav />
      <AuthGate>
        <main className="max-w-3xl mx-auto px-6 pb-24">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
            className="mt-6 mb-7"
          >
            <div className="flex items-end justify-between">
              <div>
                <h1 className="text-4xl font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
                  Your tasks
                </h1>
                <p className="text-navy/40 text-sm font-body mt-1 font-light">
                  {tasks.filter(t => t.status !== 'completed').length} remaining · {tasks.filter(t => t.status === 'completed').length} complete
                </p>
              </div>
              <button
                onClick={runAudit}
                disabled={auditLoading}
                className="text-sm font-semibold text-white font-body rounded-xl px-4 py-2.5 transition-transform hover:-translate-y-0.5 disabled:opacity-60 flex items-center gap-2"
                style={{ background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)', boxShadow: '0 4px 16px rgba(109,143,216,0.4)' }}
              >
                {auditLoading ? 'Auditing…' : '✦ Audit backlog'}
              </button>
            </div>
          </motion.div>

          {/* Audit result */}
          {auditResult && auditResult.candidates?.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-5 mb-5 border border-amber/30"
            >
              <div className="flex items-center gap-2 mb-3">
                <span>🌊</span>
                <span className="text-sm font-medium text-navy font-body">Backlog health: {auditResult.health_score}/100</span>
              </div>
              <div className="space-y-3">
                {auditResult.candidates.slice(0, 5).map((c: any) => (
                  <div key={c.task_id} className="border-b border-navy/5 last:border-0 pb-3 last:pb-0">
                    <div className="flex items-start gap-2 mb-1.5">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full font-body ${c.recommendation === 'abandon' ? 'bg-coral/15 text-coral' : 'bg-amber/20 text-amber-700'}`}>
                        {c.recommendation}
                      </span>
                      <span className="text-xs text-navy/60 font-body flex-1">{c.task_title} — {c.reason}</span>
                    </div>
                    <div className="flex gap-1.5 pl-1">
                      {(['abandon', 'delegate', 'defer'] as const).map(a => (
                        <button
                          key={a}
                          onClick={() => applyAudit(c.task_id, a)}
                          className={`text-[11px] font-body px-2.5 py-1 rounded-lg transition-all hover:-translate-y-0.5 ${a === c.recommendation ? 'text-white' : 'text-navy/55 glass-card'}`}
                          style={a === c.recommendation ? { background: a === 'abandon' ? '#E08A76' : 'linear-gradient(135deg,#6D8FD8,#8BA5E0)' } : {}}
                        >
                          {a === 'abandon' ? '🗑 Abandon' : a === 'delegate' ? '🤝 Delegate' : '⏳ Defer 2w'}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Filters */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
            {FILTERS.map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`flex-shrink-0 px-4 py-1.5 rounded-2xl text-sm font-medium font-body transition-all duration-200 ${filter === f.key ? 'text-white' : 'text-navy/50 hover:text-navy/70 glass-card'}`}
                style={filter === f.key ? {
                  background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)',
                  boxShadow: '0 2px 12px rgba(109,143,216,0.3)',
                } : {}}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Task groups */}
          {loading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 rounded-full border-2 border-night-blue/20 border-t-night-blue animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <div className="text-3xl mb-3 opacity-30">✦</div>
              <p className="text-navy/35 text-sm font-body">Nothing here yet</p>
            </div>
          ) : (
            <div className="space-y-8">
              {Array.from(byCluster.entries()).map(([cluster, clusterTasks], gi) => (
                <motion.div
                  key={cluster}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: gi * 0.1, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="constellation-dot" style={{ width: 5, height: 5 }} />
                    <span className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">
                      {cluster}
                    </span>
                    <div className="h-px flex-1 bg-navy/5" />
                    <span className="text-[10px] text-navy/25 font-body">{clusterTasks.length}</span>
                  </div>
                  <div className="space-y-3">
                    {clusterTasks.map(t => (
                      <TaskCard key={t.id} task={t} onUpdate={load} />
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </main>

        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.5, type: 'spring', stiffness: 260, damping: 20 }}
          whileHover={{ scale: 1.08, y: -2 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setCreateOpen(true)}
          className="fixed bottom-8 right-8 w-14 h-14 rounded-full text-white text-xl flex items-center justify-center z-20 animate-glow-pulse"
          style={{
            background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)',
            boxShadow: '0 6px 24px rgba(109, 143, 216, 0.45)',
          }}
        >
          +
        </motion.button>

        <CreateTaskModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={load} />
      </AuthGate>
    </div>
  )
}
