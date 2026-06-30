'use client'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Task, quadrantInfo, skillColor } from '@/lib/types'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import ProcrastinationInsight from './ProcrastinationInsight'
import ContextSave from './ContextSave'
import RescheduleModal from './RescheduleModal'
import CascadeBadge from './CascadeBadge'
import CompletionBurst from './CompletionBurst'

const COMPLEXITY_DOTS: Record<string, string> = {
  low: '#7EBF95',
  medium: '#F5C96A',
  high: '#E8A090',
}

interface Props {
  task: Task
  onUpdate?: () => void
  compact?: boolean
}

export default function TaskCard({ task, onUpdate, compact = false }: Props) {
  const { token } = useAuth()
  const q = quadrantInfo(task.eisenhower_quadrant)
  const [reschedOpen, setReschedOpen] = useState(false)
  const [celebrating, setCelebrating] = useState(false)

  const handleComplete = async () => {
    if (!token || celebrating) return
    try {
      await api.completeTask(token, task.id)
      setCelebrating(true)  // burst plays, then refreshes via onDone
    } catch {}
  }

  const handleStart = async () => {
    if (!token) return
    try {
      await api.updateTask(token, task.id, { status: 'in_progress' })
      onUpdate?.()
    } catch {}
  }

  const daysUntil = task.deadline
    ? Math.ceil((new Date(task.deadline).getTime() - Date.now()) / 86400000)
    : null

  return (
    <motion.div
      whileHover={{ y: -3, boxShadow: '0 8px 32px rgba(109,143,216,0.14)' }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="glass-card p-5 group cursor-default relative"
    >
      {celebrating && (
        <CompletionBurst onDone={() => { setCelebrating(false); onUpdate?.() }} />
      )}
      <div className="flex items-start gap-3">
        {/* Complete checkbox */}
        <button
          onClick={handleComplete}
          className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full border-2 border-navy/20 hover:border-sage hover:bg-sage/10 transition-all duration-200 flex items-center justify-center"
          title="Mark complete"
        >
          <div className="w-2 h-2 rounded-full bg-transparent group-hover:bg-sage transition-colors duration-200" />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`font-medium text-navy truncate font-body ${compact ? 'text-[14px]' : 'text-[15px]'}`}>
              {task.title}
            </h3>
          </div>

          {!compact && task.description && (
            <p className="text-navy/45 text-[13px] font-body font-light mb-3 line-clamp-2 leading-relaxed">
              {task.description}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            {/* Quadrant badge */}
            {q && (
              <span
                className="skill-badge"
                style={{ background: q.bg, color: q.dot }}
              >
                {q.label}
              </span>
            )}

            {/* Skill tags */}
            {(task.skill_tags || []).slice(0, 3).map(skill => {
              const c = skillColor(skill)
              return (
                <span key={skill} className="skill-badge" style={{ background: c.bg, color: c.fg }}>
                  {skill}
                </span>
              )
            })}

            {/* Complexity dot */}
            <div className="flex items-center gap-1">
              <div
                className="w-2 h-2 rounded-full"
                style={{ background: COMPLEXITY_DOTS[task.complexity] || '#B8A9D4' }}
              />
              <span className="text-[11px] text-navy/35 font-body">{task.estimated_hours}h</span>
            </div>

            {/* Deadline */}
            {daysUntil !== null && (
              <span className={`text-[11px] font-body ${daysUntil <= 1 ? 'text-coral font-medium' : daysUntil <= 3 ? 'text-amber-600' : 'text-navy/35'}`}>
                {daysUntil === 0 ? 'today' : daysUntil < 0 ? 'overdue' : `${daysUntil}d`}
              </span>
            )}

            {/* Rescheduled */}
            {task.reschedule_count > 0 && (
              <span className="text-[11px] text-navy/25 font-body">↺ {task.reschedule_count}</span>
            )}
          </div>
        </div>
      </div>

      {/* Cascade — click to see which tasks this blocks */}
      <CascadeBadge taskId={task.id} severity={task.cascade_severity || 0} />

      {/* Procrastination insight + context save + reschedule — only on full active cards */}
      {!compact && task.status !== 'completed' && task.status !== 'abandoned' && (
        <>
          <ProcrastinationInsight taskId={task.id} onStartFirstStep={handleStart} />
          <ContextSave taskId={task.id} />
          <button
            onClick={() => setReschedOpen(true)}
            className="mt-2 text-[11px] font-body text-navy/45 hover:text-navy/70 transition-colors flex items-center gap-1.5"
          >
            <span>🗓️</span> Reschedule
          </button>
          <RescheduleModal
            task={task}
            open={reschedOpen}
            onClose={() => setReschedOpen(false)}
            onDone={() => onUpdate?.()}
          />
        </>
      )}
    </motion.div>
  )
}
