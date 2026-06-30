'use client'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export default function DailyBrief() {
  const { token } = useAuth()
  const [brief, setBrief] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  const fetchBrief = async () => {
    if (!token || loading) return
    setLoading(true)
    setOpen(true)
    try {
      const data = await api.getMorningBrief(token)
      setBrief(data.brief || 'Your sky is clear — add a task to get a tailored brief.')
    } catch {
      setBrief('Your planner is resting right now. Check back in a moment.')
    } finally {
      setLoading(false)
    }
  }

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card p-6 relative overflow-hidden"
    >
      {/* Moon glow in top-right */}
      <div
        className="absolute -top-8 -right-8 w-32 h-32 rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(245,201,106,0.12) 0%, transparent 70%)',
        }}
      />

      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-lg">🌙</span>
            <span className="text-xs font-medium text-navy/40 tracking-widest uppercase font-body">
              Daily Clarity
            </span>
          </div>
          <h2
            className="text-2xl font-bold text-navy leading-tight mb-1"
            style={{ fontFamily: 'Fraunces, serif' }}
          >
            {greeting}
          </h2>
          <p className="text-navy/50 text-sm font-body font-light">
            Let's find one good place to begin.
          </p>
        </div>

        <button
          onClick={fetchBrief}
          disabled={loading}
          className="flex-shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-2xl text-white text-sm font-medium font-body transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-60"
          style={{
            background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)',
            boxShadow: '0 4px 16px rgba(109, 143, 216, 0.3)',
          }}
        >
          {loading ? (
            <>
              <div className="w-3.5 h-3.5 rounded-full border border-white/40 border-t-white animate-spin" />
              Thinking…
            </>
          ) : (
            <>✦ Ask Gemini</>
          )}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-5 pt-5 border-t border-navy/8">
              {loading ? (
                <div className="flex gap-1.5 py-2">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-2 h-2 rounded-full bg-night-blue/40 animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-navy/75 text-[15px] font-body font-light leading-relaxed whitespace-pre-wrap">
                  {brief}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
