'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { useTheme } from '@/lib/theme-context'
import { motion } from 'framer-motion'
import StreakFlame from './StreakFlame'

export default function Nav({ onAdd }: { onAdd?: () => void }) {
  const { user, signIn, signOut, calendarConnected, connectCalendar } = useAuth()
  const { theme, toggle } = useTheme()
  const path = usePathname()

  const links = [
    { href: '/', label: 'Today' },
    { href: '/tasks', label: 'All Tasks' },
    { href: '/journey', label: 'Journey' },
  ]

  return (
    <nav className="flex items-center justify-between px-6 pt-6 pb-3 gap-4">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 flex-shrink-0">
        <span style={{ color: 'var(--amber)', fontSize: 18 }}>✦</span>
        <span style={{ fontFamily: 'Fraunces, serif', color: 'var(--text)', fontSize: 17, fontWeight: 700 }}>
          Life Saver
        </span>
      </Link>

      {/* Nav pills */}
      <div className="flex items-center gap-0.5 card px-2 py-1.5 rounded-2xl">
        {links.map(l => (
          <Link key={l.href} href={l.href} className="relative px-4 py-1.5 rounded-xl text-sm font-medium transition-colors duration-200"
            style={{ color: path === l.href ? 'var(--text)' : 'var(--text-muted)' }}
          >
            {path === l.href && (
              <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-xl"
                style={{ background: 'var(--surface-hover)', border: '1px solid var(--border)' }}
                transition={{ type: 'spring', stiffness: 400, damping: 35 }}
              />
            )}
            <span className="relative z-10">{l.label}</span>
          </Link>
        ))}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {user && <StreakFlame />}

        {/* Calendar connect */}
        {user && !calendarConnected && (
          <button onClick={connectCalendar}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium card transition-colors"
            style={{ color: 'var(--text-muted)' }}
            title="Connect Google Calendar so scheduling can read/write real events"
          >
            📅 Connect Calendar
          </button>
        )}

        {/* Add task button */}
        {onAdd && (
          <button onClick={onAdd}
            className="flex items-center gap-1.5 px-4 py-2 rounded-2xl text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 anim-pulse-glow"
            style={{ background: 'linear-gradient(135deg, var(--blue) 0%, var(--blue-bright) 100%)' }}
          >
            <span>+</span> Add Task
          </button>
        )}

        {/* Theme toggle */}
        <button onClick={toggle}
          className="w-9 h-9 card rounded-full flex items-center justify-center text-base hover:scale-110 transition-transform"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '☀' : '🌙'}
        </button>

        {/* User */}
        {user ? (
          <button onClick={signOut} className="flex items-center gap-2 text-sm transition-colors"
            style={{ color: 'var(--text-muted)' }}
          >
            {user.photoURL
              ? <img src={user.photoURL} alt="" className="w-7 h-7 rounded-full" />
              : <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: 'var(--blue)', color: '#fff' }}
                >{user.displayName?.[0] ?? '?'}</div>
            }
            <span className="hidden sm:inline font-medium">{user.displayName?.split(' ')[0]}</span>
          </button>
        ) : (
          <button onClick={signIn} className="text-sm font-semibold transition-colors"
            style={{ color: 'var(--blue)' }}
          >
            Sign in
          </button>
        )}
      </div>
    </nav>
  )
}
