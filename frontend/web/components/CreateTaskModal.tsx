'use client'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { Task, isActive } from '@/lib/types'

interface Props {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

export default function CreateTaskModal({ open, onClose, onCreated }: Props) {
  const { token } = useAuth()
  const [form, setForm] = useState({
    title: '',
    description: '',
    deadline: '',
    estimated_hours: '1',
    complexity: 'medium',
  })
  const [dependsOn, setDependsOn] = useState<string[]>([])
  const [existing, setExisting] = useState<Task[]>([])
  const [inflation, setInflation] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [voiceMode, setVoiceMode] = useState(false)
  const [recording, setRecording] = useState(false)
  const [mediaRec, setMediaRec] = useState<MediaRecorder | null>(null)

  useEffect(() => {
    if (!open || !token) return
    api.getTasks(token).then(ts => setExisting(ts.filter(isActive))).catch(() => setExisting([]))
    api.getPlanningSummary(token)
      .then(s => setInflation(s.sample_count >= 2 ? s.overall_inflation : null))
      .catch(() => setInflation(null))
  }, [open, token])

  const estNum = parseFloat(form.estimated_hours) || 0
  const showHint = inflation != null && inflation >= 1.15 && estNum > 0
  const suggested = showHint ? Math.round(estNum * inflation! * 10) / 10 : 0

  const toggleDep = (id: string) =>
    setDependsOn(d => d.includes(id) ? d.filter(x => x !== id) : [...d, id])

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !form.title.trim()) return
    setSaving(true)
    try {
      await api.createTask(token, {
        title: form.title.trim(),
        description: form.description || undefined,
        deadline: form.deadline ? new Date(form.deadline).toISOString() : undefined,
        estimated_hours: parseFloat(form.estimated_hours) || 1,
        complexity: form.complexity,
        depends_on: dependsOn,
      })
      setForm({ title: '', description: '', deadline: '', estimated_hours: '1', complexity: 'medium' })
      setDependsOn([])
      onCreated()
      onClose()
    } catch {}
    finally { setSaving(false) }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      const chunks: Blob[] = []
      rec.ondataavailable = e => chunks.push(e.data)
      rec.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const fd = new FormData()
        fd.append('audio', blob, 'recording.webm')
        if (!token) return
        setSaving(true)
        try {
          const data = await api.transcribeAndCreate(token, fd)
          onCreated()
          onClose()
        } finally { setSaving(false) }
        stream.getTracks().forEach(t => t.stop())
      }
      rec.start()
      setMediaRec(rec)
      setRecording(true)
    } catch {}
  }

  const stopRecording = () => {
    mediaRec?.stop()
    setRecording(false)
    setMediaRec(null)
  }

  const inputClass = "w-full px-4 py-3 rounded-xl border border-navy/10 bg-[var(--field-bg)] text-navy placeholder-navy/30 text-sm font-body focus:outline-none focus:border-night-blue/40 transition-all duration-200"

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'rgba(6, 9, 20, 0.94)', backdropFilter: 'blur(10px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ opacity: 0, y: 32, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="modal-panel w-full max-w-md p-7 relative"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-navy" style={{ fontFamily: 'Fraunces, serif' }}>
                  Add a task
                </h2>
                <p className="text-navy/40 text-xs font-body mt-0.5">One small step at a time ✦</p>
              </div>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-full bg-navy/5 hover:bg-navy/10 flex items-center justify-center text-navy/40 hover:text-navy/60 transition-all"
              >
                ✕
              </button>
            </div>

            {/* Voice / Text toggle */}
            <div className="flex gap-2 mb-5 p-1 glass-card rounded-2xl">
              {['text', 'voice'].map(m => (
                <button
                  key={m}
                  onClick={() => setVoiceMode(m === 'voice')}
                  className={`flex-1 py-2 rounded-xl text-sm font-medium font-body transition-all duration-200 ${voiceMode === (m === 'voice') ? 'bg-white text-navy shadow-sm' : 'text-navy/40 hover:text-navy/60'}`}
                >
                  {m === 'text' ? '✍ Type' : '🎤 Voice'}
                </button>
              ))}
            </div>

            {voiceMode ? (
              <div className="flex flex-col items-center py-8 gap-5">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={recording ? stopRecording : startRecording}
                  disabled={saving}
                  className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl transition-all duration-300 ${recording ? 'bg-coral/20 border-2 border-coral animate-pulse' : 'border-2 border-night-blue/30 hover:border-night-blue bg-night-blue/5'}`}
                >
                  {saving ? '✦' : recording ? '⏹' : '🎤'}
                </motion.button>
                <p className="text-navy/50 text-sm font-body text-center">
                  {saving ? 'Gemini is thinking…' : recording ? 'Recording… tap to stop' : 'Tap to speak your task'}
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <input
                  className={inputClass}
                  placeholder="What needs to happen? *"
                  value={form.title}
                  onChange={set('title')}
                  required
                  autoFocus
                />
                <textarea
                  className={inputClass}
                  placeholder="Any details? (optional)"
                  value={form.description}
                  onChange={set('description')}
                  rows={2}
                  style={{ resize: 'none' }}
                />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] uppercase tracking-widest text-navy/45 font-body mb-1">Deadline</label>
                    <input
                      type="date"
                      className={inputClass}
                      value={form.deadline}
                      onChange={set('deadline')}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase tracking-widest text-navy/45 font-body mb-1">Est. hours</label>
                    <input
                      type="number"
                      inputMode="decimal"
                      className={inputClass}
                      placeholder="e.g. 2"
                      value={form.estimated_hours}
                      onChange={set('estimated_hours')}
                      min="0.25"
                      step="any"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-widest text-navy/45 font-body mb-1">Difficulty</label>
                  <select className={inputClass} value={form.complexity} onChange={set('complexity')}>
                    <option value="low">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="high">Hard</option>
                  </select>
                </div>

                {showHint && (
                  <div className="rounded-xl p-3 flex items-start gap-2" style={{ background: '#FBEFD6' }}>
                    <span className="text-sm">📈</span>
                    <p className="text-[12px] font-body leading-relaxed" style={{ color: '#46402A' }}>
                      You estimated {estNum}h. Your completed tasks run <b>{inflation}×</b> longer than planned —
                      consider <button type="button" onClick={() => setForm(f => ({ ...f, estimated_hours: String(suggested) }))} className="font-bold underline" style={{ color: '#8A5A00' }}>~{suggested}h</button>.
                    </p>
                  </div>
                )}

                {existing.length > 0 && (
                  <div>
                    <p className="text-[11px] uppercase tracking-widest text-navy/40 font-body mb-2">
                      Depends on <span className="text-navy/25 normal-case tracking-normal">(blocks this task until done)</span>
                    </p>
                    <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                      {existing.map(t => (
                        <button
                          type="button"
                          key={t.id}
                          onClick={() => toggleDep(t.id)}
                          className={`text-[12px] font-body px-2.5 py-1 rounded-full transition-all ${dependsOn.includes(t.id) ? 'text-white' : 'text-navy/55 glass-card'}`}
                          style={dependsOn.includes(t.id) ? { background: 'linear-gradient(135deg,#6D8FD8,#8BA5E0)' } : {}}
                          title={t.title}
                        >
                          {dependsOn.includes(t.id) ? '✓ ' : ''}{t.title.length > 28 ? t.title.slice(0, 28) + '…' : t.title}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={saving || !form.title.trim()}
                  className="w-full py-3 rounded-2xl text-white text-sm font-medium font-body transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-50"
                  style={{
                    background: 'linear-gradient(135deg, #6D8FD8 0%, #8BA5E0 100%)',
                    boxShadow: '0 4px 16px rgba(109, 143, 216, 0.3)',
                  }}
                >
                  {saving ? 'Adding…' : '✦ Add task'}
                </button>
              </form>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
