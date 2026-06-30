'use client'
import { motion } from 'framer-motion'
import { useEffect } from 'react'

const TEAL = '#00E5CC'
const N = 14

interface Props {
  onDone: () => void
}

/** A teal comet/particle burst played once when a task is completed. */
export default function CompletionBurst({ onDone }: Props) {
  useEffect(() => {
    const t = setTimeout(onDone, 900)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none overflow-visible">
      {/* central flash */}
      <motion.div
        initial={{ scale: 0, opacity: 0.8 }}
        animate={{ scale: 3, opacity: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="absolute w-10 h-10 rounded-full"
        style={{ background: `radial-gradient(circle, ${TEAL}88 0%, transparent 70%)` }}
      />
      {/* checkmark pop */}
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: [0, 1.3, 1], opacity: [0, 1, 0] }}
        transition={{ duration: 0.9, ease: 'easeOut' }}
        className="absolute text-2xl"
        style={{ color: TEAL, textShadow: `0 0 12px ${TEAL}` }}
      >
        ✓
      </motion.div>
      {/* particles */}
      {Array.from({ length: N }).map((_, i) => {
        const angle = (i / N) * Math.PI * 2
        const dist = 50 + Math.random() * 40
        return (
          <motion.span
            key={i}
            initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
            animate={{
              x: Math.cos(angle) * dist,
              y: Math.sin(angle) * dist,
              opacity: 0,
              scale: 0.3,
            }}
            transition={{ duration: 0.7 + Math.random() * 0.2, ease: 'easeOut' }}
            className="absolute rounded-full"
            style={{
              width: 6, height: 6,
              background: i % 3 === 0 ? '#7EBF95' : TEAL,
              boxShadow: `0 0 8px ${TEAL}`,
            }}
          />
        )
      })}
    </div>
  )
}
