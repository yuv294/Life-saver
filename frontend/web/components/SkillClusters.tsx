'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Cluster, skillColor } from '@/lib/types'

export default function SkillClusters() {
  const { token } = useAuth()
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    api.getClusters(token)
      .then(r => setClusters(r.clusters ?? []))
      .catch(() => setClusters([]))
      .finally(() => setLoading(false))
  }, [token])

  if (loading || clusters.length === 0) return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">◈</span>
        <span className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">
          Cognitive sessions — batch by skill
        </span>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {clusters.map((c, i) => {
          const col = skillColor(c.dominant_skill)
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.07, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="glass-card p-4 flex-shrink-0 w-48"
              style={{ borderTop: `3px solid ${col.fg}` }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="skill-badge" style={{ background: col.bg, color: col.fg }}>
                  {c.dominant_skill}
                </span>
                <span className="text-[11px] text-navy/40 font-body">
                  ~{Math.round(c.estimated_total_hours)}h
                </span>
              </div>
              <p className="text-[14px] font-medium text-navy font-body leading-snug">{c.name}</p>
              <p className="text-[12px] text-navy/45 font-body mt-1">
                {c.task_ids.length} task{c.task_ids.length === 1 ? '' : 's'} share this focus
              </p>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
