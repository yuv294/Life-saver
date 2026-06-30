'use client'
import { motion } from 'framer-motion'

interface Props {
  value: number // 0–100
  label?: string
}

export default function MomentumMeter({ value, label = 'Momentum' }: Props) {
  const r = 54
  const circ = 2 * Math.PI * r
  const progress = (value / 100) * circ
  const color = value >= 70 ? '#7EBF95' : value >= 40 ? '#6D8FD8' : '#B8A9D4'

  return (
    <div className="glass-card p-6 flex flex-col items-center gap-3">
      <div className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">{label}</div>
      <div className="relative">
        <svg width="130" height="130" className="-rotate-90">
          <circle cx="65" cy="65" r={r} fill="none" stroke="rgba(26,31,53,0.06)" strokeWidth="8" />
          <motion.circle
            cx="65" cy="65" r={r}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - progress }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 8px ${color}60)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-3xl font-bold text-navy leading-none"
            style={{ fontFamily: 'Fraunces, serif' }}
          >
            {value}
          </span>
          <span className="text-[10px] text-navy/30 font-body uppercase tracking-wide mt-0.5">score</span>
        </div>
      </div>
      <p className="text-center text-[13px] text-navy/50 font-body font-light leading-snug">
        {value >= 70 ? "You're in a great flow" : value >= 40 ? 'Building steady rhythm' : 'Every small step counts'}
      </p>
    </div>
  )
}
