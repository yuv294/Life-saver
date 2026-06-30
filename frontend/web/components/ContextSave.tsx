'use client'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface Props {
  taskId: string
}

export default function ContextSave({ taskId }: Props) {
  const { token } = useAuth()
  const [open, setOpen] = useState(false)
  const [breadcrumb, setBreadcrumb] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [dump, setDump] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const toggle = async () => {
    if (open) { setOpen(false); return }
    setOpen(true)
    if (breadcrumb !== null || !token) return
    setLoading(true)
    try {
      const res = await api.getContext(token, taskId)
      setBreadcrumb(res.breadcrumb)
      setSavedAt(res.saved_at ?? null)
    } catch {
      setBreadcrumb(null)
    } finally {
      setLoading(false)
    }
  }

  const save = async () => {
    if (!token || !dump.trim()) return
    setSaving(true)
    try {
      const res = await api.saveContext(token, taskId, dump.trim())
      setBreadcrumb(res.breadcrumb)
      setSavedAt(new Date().toISOString())
      setDump('')
    } catch {} finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-2">
      <button
        onClick={toggle}
        className="text-[11px] font-body text-navy/45 hover:text-navy/70 transition-colors flex items-center gap-1.5"
      >
        <span>⏸️</span>
        {open ? 'Hide context' : 'Pause & save context'}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-3">
              {loading ? (
                <div className="flex items-center gap-2 text-navy/40 text-[12px] font-body py-1">
                  <div className="w-3 h-3 rounded-full border border-night-blue/30 border-t-night-blue animate-spin" />
                  Loading your breadcrumb…
                </div>
              ) : breadcrumb ? (
                <div className="rounded-xl p-3" style={{ background: '#FBEFD6' }}>
                  <p className="text-[10px] uppercase tracking-widest font-body mb-1.5 font-semibold" style={{ color: '#8A5A00' }}>
                    🍞 Where you left off
                  </p>
                  <p className="text-[12.5px] font-body leading-relaxed whitespace-pre-wrap" style={{ color: '#3F3A2A' }}>
                    {breadcrumb}
                  </p>
                </div>
              ) : (
                <p className="text-[12px] text-navy/40 font-body">No saved context yet — jot down where you are.</p>
              )}

              <div>
                <textarea
                  value={dump}
                  onChange={(e) => setDump(e.target.value)}
                  rows={2}
                  placeholder="10-second brain dump: what's done, what you're thinking, what's next…"
                  className="w-full px-3 py-2 rounded-xl border border-navy/10 bg-[var(--field-bg)] text-navy placeholder-navy/30 text-[12.5px] font-body focus:outline-none focus:border-night-blue/40 transition-all"
                  style={{ resize: 'none' }}
                />
                <div className="flex justify-end mt-2">
                  <button
                    onClick={save}
                    disabled={saving || !dump.trim()}
                    className="text-[11px] font-medium text-white px-3 py-1.5 rounded-xl font-body transition-transform hover:-translate-y-0.5 disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)' }}
                  >
                    {saving ? 'Saving…' : '✦ Save context'}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
