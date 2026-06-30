'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { onAuthStateChanged, User as FirebaseUser, signInWithPopup, signOut, GoogleAuthProvider } from 'firebase/auth'
import { auth, googleProvider, calendarProvider } from './firebase'

interface AuthCtx {
  user: FirebaseUser | null
  token: string | null
  loading: boolean
  calendarConnected: boolean
  signIn: () => Promise<void>
  signOut: () => Promise<void>
  connectCalendar: () => Promise<boolean>
}

const AuthContext = createContext<AuthCtx>({
  user: null, token: null, loading: true, calendarConnected: false,
  signIn: async () => {}, signOut: async () => {}, connectCalendar: async () => false,
})

const CALENDAR_FLAG_KEY = 'lifesaver_calendar_connected'

// Local dev only: skip Google sign-in and use the backend's DEV_AUTH_BYPASS user.
const DEV_AUTH = process.env.NEXT_PUBLIC_DEV_AUTH === 'true'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<FirebaseUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [calendarConnected, setCalendarConnected] = useState(false)

  useEffect(() => {
    setCalendarConnected(typeof window !== 'undefined' && localStorage.getItem(CALENDAR_FLAG_KEY) === 'true')
  }, [])

  useEffect(() => {
    if (DEV_AUTH) {
      setUser({ displayName: 'Dev User', email: 'dev@lifesaver.local' } as FirebaseUser)
      setToken('dev')
      setLoading(false)
      return
    }
    return onAuthStateChanged(auth, async (u) => {
      setUser(u)
      if (u) {
        const t = await u.getIdToken()
        setToken(t)
      } else {
        setToken(null)
      }
      setLoading(false)
    })
  }, [])

  // Refresh token every 50 minutes
  useEffect(() => {
    if (!user || DEV_AUTH) return
    const interval = setInterval(async () => {
      const t = await user.getIdToken(true)
      setToken(t)
    }, 50 * 60 * 1000)
    return () => clearInterval(interval)
  }, [user])

  const handleSignIn = async () => {
    await signInWithPopup(auth, googleProvider)
  }

  const handleSignOut = async () => {
    await signOut(auth)
  }

  // Re-prompts Google sign-in with the Calendar scope added, then hands the
  // resulting OAuth access token to the backend so agents can read/write events.
  // Note: Firebase's client-side popup flow never returns a refresh token, so this
  // access token is only good for ~1 hour — the user reconnects when it goes stale.
  const connectCalendar = async (): Promise<boolean> => {
    if (DEV_AUTH) return false
    try {
      const result = await signInWithPopup(auth, calendarProvider)
      const credential = GoogleAuthProvider.credentialFromResult(result)
      if (!credential?.accessToken) return false

      const idToken = await result.user.getIdToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/users/me/oauth-tokens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${idToken}` },
        body: JSON.stringify({
          access_token: credential.accessToken,
          expiry: new Date(Date.now() + 55 * 60 * 1000).toISOString(),
        }),
      })
      if (!res.ok) return false

      localStorage.setItem(CALENDAR_FLAG_KEY, 'true')
      setCalendarConnected(true)
      return true
    } catch {
      return false
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, calendarConnected, signIn: handleSignIn, signOut: handleSignOut, connectCalendar }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
