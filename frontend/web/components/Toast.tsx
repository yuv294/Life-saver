'use client'
import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

type ToastType = 'success' | 'error' | 'info'
interface ToastItem { id: number; msg: string; type: ToastType }

const ToastCtx = createContext<{
  toast: (msg: string, type?: ToastType) => void
}>({ toast: () => {} })

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  let idRef = 0

  const toast = useCallback((msg: string, type: ToastType = 'info') => {
    const id = ++idRef
    setItems(p => [...p, { id, msg, type }])
    setTimeout(() => setItems(p => p.filter(i => i.id !== id)), 4000)
  }, [])

  const colors: Record<ToastType, string> = {
    success: 'var(--sage)',
    error:   'var(--coral)',
    info:    'var(--blue)',
  }

  return (
    <ToastCtx.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-6 left-6 z-50 flex flex-col gap-2 pointer-events-none">
        <AnimatePresence>
          {items.map(i => (
            <motion.div
              key={i.id}
              initial={{ opacity: 0, x: -20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25 }}
              className="pointer-events-auto card px-4 py-3 flex items-center gap-3 max-w-xs"
            >
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: colors[i.type] }} />
              <span className="text-sm" style={{ color: 'var(--text)' }}>{i.msg}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  )
}

export const useToast = () => useContext(ToastCtx)
