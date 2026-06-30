'use client'
import { useEffect, useRef } from 'react'
import { useTheme } from '@/lib/theme-context'

interface Star { x: number; y: number; r: number; a: number; da: number; ds: number; px: number; py: number; pf: number }
interface Shoot { x: number; y: number; a: number; active: boolean; angle: number }

export default function StarField() {
  const { theme } = useTheme()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const themeRef = useRef(theme)
  const starsRef = useRef<Star[]>([])
  const shootRef = useRef<Shoot>({ x: 0, y: 0, a: 0, active: false, angle: -0.55 })
  const mouseRef = useRef({ x: 0, y: 0 })
  const rafRef = useRef<number>()

  useEffect(() => { themeRef.current = theme }, [theme])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      buildStars()
    }

    const buildStars = () => {
      const isDark = themeRef.current === 'dark'
      const count = Math.floor((canvas.width * canvas.height) / (isDark ? 3500 : 6000))
      starsRef.current = Array.from({ length: count }, () => {
        const x = Math.random() * canvas.width
        const y = Math.random() * canvas.height
        return {
          x, y, px: x, py: y,
          r: Math.random() * (isDark ? 1.8 : 1.2) + 0.3,
          a: Math.random() * 0.6 + (isDark ? 0.3 : 0.15),
          da: Math.random() > 0.5 ? 1 : -1,
          ds: Math.random() * 0.004 + 0.001,
          pf: Math.random() * 0.02 + 0.005,
        }
      })
    }

    const scheduleShooting = () => {
      setTimeout(() => {
        const s = shootRef.current
        s.x = Math.random() * canvas.width * 0.7
        s.y = Math.random() * canvas.height * 0.35
        s.a = 1; s.active = true
        scheduleShooting()
      }, 10000 + Math.random() * 20000)
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const isDark = themeRef.current === 'dark'
      const mx = mouseRef.current.x - canvas.width / 2
      const my = mouseRef.current.y - canvas.height / 2

      for (const s of starsRef.current) {
        s.a += s.da * s.ds
        if (s.a >= (isDark ? 0.95 : 0.6)) { s.a = isDark ? 0.95 : 0.6; s.da = -1 }
        if (s.a <= (isDark ? 0.1 : 0.05)) { s.a = isDark ? 0.1 : 0.05; s.da = 1 }
        s.x = s.px + mx * s.pf
        s.y = s.py + my * s.pf

        const starColor = isDark
          ? `rgba(200, 215, 255, ${s.a})`
          : `rgba(80, 120, 210, ${s.a})`

        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fillStyle = starColor
        ctx.fill()

        if (s.r > 1.2) {
          const g = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 5)
          g.addColorStop(0, isDark ? `rgba(150,190,255,${s.a * 0.4})` : `rgba(80,120,210,${s.a * 0.2})`)
          g.addColorStop(1, 'rgba(0,0,0,0)')
          ctx.beginPath()
          ctx.arc(s.x, s.y, s.r * 5, 0, Math.PI * 2)
          ctx.fillStyle = g
          ctx.fill()
        }
      }

      // Shooting star (dark mode only)
      if (isDark) {
        const sh = shootRef.current
        if (sh.active) {
          sh.a -= 0.018
          const ex = sh.x + Math.cos(sh.angle) * 90
          const ey = sh.y + Math.sin(sh.angle) * 90
          const g = ctx.createLinearGradient(sh.x, sh.y, ex, ey)
          g.addColorStop(0, 'rgba(200,215,255,0)')
          g.addColorStop(0.5, `rgba(200,215,255,${sh.a * 0.5})`)
          g.addColorStop(1, `rgba(245,165,35,${sh.a})`)
          ctx.beginPath()
          ctx.moveTo(sh.x, sh.y)
          ctx.lineTo(ex, ey)
          ctx.strokeStyle = g
          ctx.lineWidth = 1.5
          ctx.stroke()
          if (sh.a <= 0) sh.active = false
        }
      }

      rafRef.current = requestAnimationFrame(draw)
    }

    const onMouse = (e: MouseEvent) => { mouseRef.current = { x: e.clientX, y: e.clientY } }
    resize()
    window.addEventListener('resize', resize)
    window.addEventListener('mousemove', onMouse)
    scheduleShooting()
    draw()

    return () => {
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMouse)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  return <canvas ref={canvasRef} id="star-canvas" />
}
