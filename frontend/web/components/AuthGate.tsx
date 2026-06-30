'use client'
import { useAuth } from '@/lib/auth-context'
import { motion } from 'framer-motion'

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading, signIn } = useAuth()

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-full border-2 anim-spin"
            style={{ borderColor: 'var(--border)', borderTopColor: 'var(--blue)' }} />
          <p className="text-sm" style={{ color: 'var(--text-faint)' }}>loading your sky…</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="card glow-ring p-12 max-w-md w-full text-center"
        >
          <div className="flex justify-center gap-4 mb-8">
            {[14, 22, 14].map((size, i) => (
              <span key={i} className="anim-float" style={{ fontSize: size, color: 'var(--blue)', animationDelay: `${i * 0.7}s` }}>
                {i === 1 ? '✦' : '✧'}
              </span>
            ))}
          </div>

          <h1 style={{ fontFamily: 'Fraunces, serif', color: 'var(--text)', fontSize: 40, fontWeight: 900, lineHeight: 1.1 }}>
            Priority,<br />
            <em style={{ fontStyle: 'italic', fontWeight: 300, color: 'var(--blue)' }}>not panic.</em>
          </h1>

          <p className="text-sm font-light mt-3 mb-8 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            AI-powered gentle planner — skill clustering,<br />
            procrastination fingerprinting, morning briefs.
          </p>

          <div className="flex items-center justify-center gap-2 mb-8" style={{ opacity: 0.3 }}>
            <div className="c-dot" />
            <div style={{ height: 1, width: 64, background: 'var(--blue)' }} />
            <div className="c-dot" />
            <div style={{ height: 1, width: 32, background: 'var(--blue)' }} />
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--amber)', boxShadow: '0 0 8px var(--amber)' }} />
          </div>

          <button onClick={signIn}
            className="w-full py-3.5 rounded-2xl font-semibold text-white text-sm transition-all duration-300 hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, var(--blue) 0%, var(--blue-bright) 100%)', boxShadow: '0 4px 20px rgba(109,143,216,0.4)' }}
          >
            Continue with Google
          </button>
          <p className="text-xs mt-4" style={{ color: 'var(--text-faint)' }}>Your tasks are yours. Always private.</p>
        </motion.div>
      </div>
    )
  }

  return <>{children}</>
}
