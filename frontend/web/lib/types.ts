// These types mirror the FastAPI backend responses (schemas/task.py, etc.).
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'abandoned'
export type Complexity = 'low' | 'medium' | 'high'
// Eisenhower quadrant is an integer 1-4 from the backend (Gemini-tagged).
export type Quadrant = 1 | 2 | 3 | 4

export interface Task {
  id: string
  user_id: string
  title: string
  description?: string | null
  skill_tags: string[]
  status: TaskStatus
  complexity: Complexity
  estimated_hours?: number | null
  actual_hours?: number | null
  deadline?: string | null
  scheduled_for?: string | null
  calendar_event_id?: string | null
  eisenhower_quadrant?: Quadrant | null
  importance?: string
  urgency?: string
  cascade_severity?: number
  reschedule_count: number
  procrastination_trigger?: string | null
  depends_on?: string[]
  created_at: string
  updated_at: string
}

export interface TaskCreate {
  title: string
  description?: string
  deadline?: string
  estimated_hours?: number
  complexity?: Complexity
}

export interface Cluster {
  name: string
  dominant_skill: string
  skill_tags: string[]
  task_ids: string[]
  estimated_total_hours: number
  max_cascade?: number
}

export interface EnergyWindow {
  start: string
  end: string
  energy_score: number
  label: string
}

export interface MorningBrief {
  brief: string
}

export interface RescheduleWindow {
  start: string
  end: string
  energy_score: number
  tasks_displaced: number
  cascade_impact: number
  label: string
}

export interface RescheduleOptions {
  task_id: string
  reschedule_count: number
  windows: RescheduleWindow[]
  no_options: boolean
  no_options_alternatives: string[]
  requires_reason: boolean
}

export interface User {
  id: string
  email: string
  display_name?: string
  avatar_url?: string
}

// ── Display helpers ───────────────────────────────────────────────────────────

export const isDone = (t: Task) => t.status === 'completed'
export const isActive = (t: Task) => t.status === 'pending' || t.status === 'in_progress'

export interface QuadrantInfo { label: string; bg: string; dot: string }

// Badges render as plain coloured TEXT (no pill bg). These are bright enough to
// read on the dark cards yet still legible on the light theme.
export function quadrantInfo(q?: Quadrant | null): QuadrantInfo | null {
  switch (q) {
    case 1: return { label: 'Do First', bg: 'transparent', dot: '#5BB082' }
    case 2: return { label: 'Schedule', bg: 'transparent', dot: '#6E94E0' }
    case 3: return { label: 'Delegate', bg: 'transparent', dot: '#CF9A2E' }
    case 4: return { label: 'Eliminate', bg: 'transparent', dot: '#A98AD6' }
    default: return null
  }
}

const SKILL_COLORS: Record<string, { bg: string; fg: string }> = {
  analytical:     { bg: 'transparent', fg: '#6E94E0' },
  creative:       { bg: 'transparent', fg: '#A98AD6' },
  communicative:  { bg: 'transparent', fg: '#35AEAE' },
  administrative: { bg: 'transparent', fg: '#CF9A2E' },
  relational:     { bg: 'transparent', fg: '#DE8068' },
  physical:       { bg: 'transparent', fg: '#5BB082' },
}

export function skillColor(skill: string) {
  return SKILL_COLORS[skill] || { bg: 'transparent', fg: '#8FA0C0' }
}
