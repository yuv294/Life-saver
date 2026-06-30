'use client'
import { useEffect, useRef, useMemo, useState } from 'react'
import { Task } from '@/lib/types'

interface Props {
  tasks: Task[]
  width?: number
  height?: number
}

// Bright glow colours keyed to the REAL skill tags (so each constellation is distinct).
const SKILL_GLOW: Record<string, string> = {
  analytical:     '#6D8FD8',
  creative:       '#B8A9D4',
  communicative:  '#5BC8C8',
  administrative: '#F5C96A',
  relational:     '#E8A090',
  physical:       '#7EBF95',
}
const DEFAULT_GLOW = '#8AA0C8'

function clusterColor(name?: string): string {
  if (!name) return DEFAULT_GLOW
  return SKILL_GLOW[name] || DEFAULT_GLOW
}

function hexRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
}
// lerp a colour toward white for a hot stellar core
function lighten([r, g, b]: [number, number, number], t: number): [number, number, number] {
  return [Math.round(r + (255 - r) * t), Math.round(g + (255 - g) * t), Math.round(b + (255 - b) * t)]
}

export default function ConstellationMap({ tasks, width: widthProp = 600, height = 360 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  // measure the container so the sky fills the available width and grows with it
  const [width, setWidth] = useState(widthProp)
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const measure = () => setWidth(Math.max(280, el.clientWidth - 40)) // minus p-5 padding
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  interface Node {
    x: number; y: number; task: Task; r: number; color: string; rgb: [number, number, number]
    done: boolean; base: number; phase: number; tw: number
  }

  const nodes = useMemo<Node[]>(() => {
    const clusters = new Map<string, Task[]>()
    for (const t of tasks) {
      const key = (t.skill_tags && t.skill_tags[0]) || 'general'
      if (!clusters.has(key)) clusters.set(key, [])
      clusters.get(key)!.push(t)
    }

    const result: Node[] = []
    const clusterKeys = Array.from(clusters.keys())
    const cx = width / 2
    const cy = height / 2
    const clusterRadius = Math.min(width, height) * 0.34

    clusterKeys.forEach((ckey, ci) => {
      const clusterTasks = clusters.get(ckey)!
      const angle = (ci / clusterKeys.length) * Math.PI * 2 - Math.PI / 2
      const ccx = cx + Math.cos(angle) * clusterRadius * (clusterKeys.length === 1 ? 0 : 0.85)
      const ccy = cy + Math.sin(angle) * clusterRadius * (clusterKeys.length === 1 ? 0 : 0.85)
      const color = clusterColor(ckey)

      clusterTasks.forEach((task, ti) => {
        const a2 = (ti / Math.max(clusterTasks.length, 1)) * Math.PI * 2
        const spread = clusterTasks.length === 1 ? 0 : 26 + clusterTasks.length * 3
        const x = ccx + Math.cos(a2) * spread + (Math.random() - 0.5) * 14
        const y = ccy + Math.sin(a2) * spread + (Math.random() - 0.5) * 14
        const done = task.status === 'completed'
        const r = done ? 2.8 : 1.6 + Math.min(2, (task.cascade_severity || 0) * 0.5)
        result.push({
          x: Math.max(14, Math.min(width - 14, x)),
          y: Math.max(14, Math.min(height - 14, y)),
          task, r, color, rgb: hexRgb(color), done,
          base: done ? 1 : 0.55,
          phase: Math.random() * Math.PI * 2,
          tw: 0.7 + Math.random() * 1.6,
        })
      })
    })
    return result
  }, [tasks, width, height])

  // faint background "dust" stars for realism (stable positions)
  const dust = useMemo(() =>
    Array.from({ length: 46 }, () => ({
      x: Math.random() * width, y: Math.random() * height,
      r: Math.random() * 0.9 + 0.3, phase: Math.random() * Math.PI * 2,
      tw: 0.4 + Math.random() * 1.2,
    })), [width, height])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let raf = 0
    const TWO_PI = Math.PI * 2

    // precompute constellation line pairs (consecutive same-skill stars)
    const byCluster = new Map<string, Node[]>()
    for (const n of nodes) {
      const key = (n.task.skill_tags && n.task.skill_tags[0]) || 'general'
      if (!byCluster.has(key)) byCluster.set(key, [])
      byCluster.get(key)!.push(n)
    }
    const pairs: [Node, Node][] = []
    byCluster.forEach((g) => { for (let i = 0; i < g.length - 1; i++) pairs.push([g[i], g[i + 1]]) })

    const render = () => {
      const t = performance.now() / 1000

      // night-sky backdrop (so colours pop in both light & dark themes)
      const bg = ctx.createLinearGradient(0, 0, 0, height)
      bg.addColorStop(0, '#070B17'); bg.addColorStop(1, '#0E1830')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, width, height)

      // dust
      for (const d of dust) {
        const a = 0.18 + 0.22 * (0.5 + 0.5 * Math.sin(t * d.tw + d.phase))
        ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, TWO_PI)
        ctx.fillStyle = `rgba(200,215,255,${a})`; ctx.fill()
      }

      // constellation lines
      for (const [a, b] of pairs) {
        const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y)
        const [ar, ag, ab] = a.rgb, [br, bg2, bb] = b.rgb
        grad.addColorStop(0, `rgba(${ar},${ag},${ab},0.16)`)
        grad.addColorStop(1, `rgba(${br},${bg2},${bb},0.16)`)
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
        ctx.strokeStyle = grad; ctx.lineWidth = 1; ctx.setLineDash([2, 5]); ctx.stroke(); ctx.setLineDash([])
      }

      // stars
      for (const n of nodes) {
        const tw = n.base * (0.6 + 0.4 * Math.sin(t * n.tw + n.phase))
        const [R, G, B] = n.rgb

        // outer bloom
        const bloom = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 7)
        bloom.addColorStop(0, `rgba(${R},${G},${B},${0.30 * tw})`)
        bloom.addColorStop(1, 'rgba(0,0,0,0)')
        ctx.fillStyle = bloom; ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 7, 0, TWO_PI); ctx.fill()

        // inner glow
        const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 3)
        glow.addColorStop(0, `rgba(${R},${G},${B},${0.75 * tw})`)
        glow.addColorStop(1, 'rgba(0,0,0,0)')
        ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 3, 0, TWO_PI); ctx.fill()

        // diffraction spikes for completed stars
        if (n.done) {
          const len = n.r * (4.5 + 1.8 * Math.sin(t * n.tw + n.phase))
          const drawSpike = (hx: number, hy: number) => {
            const g = ctx.createLinearGradient(n.x - hx, n.y - hy, n.x + hx, n.y + hy)
            g.addColorStop(0, 'rgba(0,0,0,0)')
            g.addColorStop(0.5, `rgba(${R},${G},${B},${0.55 * tw})`)
            g.addColorStop(1, 'rgba(0,0,0,0)')
            ctx.strokeStyle = g; ctx.lineWidth = 1
            ctx.beginPath(); ctx.moveTo(n.x - hx, n.y - hy); ctx.lineTo(n.x + hx, n.y + hy); ctx.stroke()
          }
          drawSpike(len, 0); drawSpike(0, len)
        }

        // white-hot core with a hint of the skill hue
        const [cr, cg, cb] = lighten(n.rgb, n.done ? 0.75 : 0.55)
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, TWO_PI)
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${Math.min(1, 0.8 + 0.2 * tw)})`
        ctx.fill()
      }

      raf = requestAnimationFrame(render)
    }
    render()
    return () => cancelAnimationFrame(raf)
  }, [nodes, dust, width, height])

  const skillsPresent = Array.from(
    new Set(tasks.map(t => (t.skill_tags && t.skill_tags[0]) || 'general'))
  )

  return (
    <div ref={wrapRef} className="glass-card p-5 overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-[15px] font-bold text-navy font-display" style={{ fontFamily: 'Fraunces, serif' }}>
            Your skill sky
          </h3>
          <p className="text-[11px] text-navy/45 font-body mt-0.5">
            Every task is a star, grouped into a constellation by skill. Finished ones shine bright; the rest glow faintly.
          </p>
        </div>
        <div className="flex gap-3 flex-shrink-0">
          <div className="flex items-center gap-1.5"><span className="text-[12px]" style={{ color: '#F5C96A' }}>✦</span><span className="text-[10px] text-navy/45 font-body">done</span></div>
          <div className="flex items-center gap-1.5"><span className="text-[12px] text-navy/30">○</span><span className="text-[10px] text-navy/45 font-body">to do</span></div>
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="text-4xl mb-3 opacity-30">✦</div>
          <p className="text-navy/35 text-sm font-body">Add tasks to light up your sky</p>
        </div>
      ) : (
        <>
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            className="w-full rounded-2xl"
            style={{ maxHeight: height }}
          />
          {/* skill → colour legend (which constellation is which) */}
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 pt-3 border-t border-navy/8">
            {skillsPresent.map(skill => (
              <div key={skill} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: clusterColor(skill), boxShadow: `0 0 6px ${clusterColor(skill)}` }} />
                <span className="text-[11px] text-navy/60 font-body capitalize">{skill}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
