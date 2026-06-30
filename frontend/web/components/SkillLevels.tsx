'use client'
import { motion } from 'framer-motion'
import { Task, isDone, skillColor } from '@/lib/types'

/** Skill levels: every 2 completed tasks in a category = +1 level (8 → Level 4). */
export default function SkillLevels({ tasks }: { tasks: Task[] }) {
  const counts: Record<string, number> = {}
  for (const t of tasks) {
    if (!isDone(t)) continue
    for (const s of t.skill_tags || []) counts[s] = (counts[s] || 0) + 1
  }
  const skills = Object.entries(counts)
    .map(([skill, n]) => ({ skill, n, level: Math.max(1, Math.ceil(n / 2)), prog: (n % 2) / 2 }))
    .sort((a, b) => b.n - a.n)

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-base">🎖️</span>
        <div>
          <h3 className="text-[15px] font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
            Skill levels
          </h3>
          <p className="text-[11px] text-navy/40 font-body mt-0.5">Every 2 completions levels up a skill</p>
        </div>
      </div>

      {skills.length === 0 ? (
        <p className="text-navy/35 text-sm font-body text-center py-6">Complete tasks to level up your skills</p>
      ) : (
        <div className="space-y-3">
          {skills.map(({ skill, n, level, prog }, i) => {
            const col = skillColor(skill)
            return (
              <motion.div key={skill} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[13px] font-medium text-navy font-body capitalize">{skill}</span>
                  <span className="skill-badge" style={{ background: col.bg, color: col.fg }}>Level {level}</span>
                </div>
                <div className="h-1.5 bg-navy/6 rounded-full overflow-hidden">
                  <motion.div className="h-full rounded-full"
                    style={{ background: col.fg }}
                    initial={{ width: 0 }} animate={{ width: `${prog * 100 || 100}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }} />
                </div>
                <p className="text-[10px] text-navy/35 font-body mt-0.5">{n} completed</p>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
