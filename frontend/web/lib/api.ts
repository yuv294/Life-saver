import { Task, Cluster, EnergyWindow, RescheduleOptions } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function req<T>(path: string, token: string | null, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  // Some endpoints (204) have no body
  const text = await res.text()
  return (text ? JSON.parse(text) : null) as T
}

export const api = {
  // Tasks
  getTasks: (token: string) =>
    req<Task[]>('/tasks', token),
  getTask: (token: string, id: string) =>
    req<Task>(`/tasks/${id}`, token),
  createTask: (token: string, body: any) =>
    req<Task>('/tasks', token, { method: 'POST', body: JSON.stringify(body) }),
  updateTask: (token: string, id: string, body: any) =>
    req<Task>(`/tasks/${id}`, token, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteTask: (token: string, id: string) =>
    req<any>(`/tasks/${id}`, token, { method: 'DELETE' }),
  completeTask: (token: string, id: string, actual_hours?: number) =>
    req<Task>(`/tasks/${id}/complete`, token, {
      method: 'POST',
      body: JSON.stringify(actual_hours != null ? { actual_hours } : {}),
    }),
  getRescheduleOptions: (token: string, id: string) =>
    req<RescheduleOptions>(`/tasks/${id}/reschedule-options`, token),
  rescheduleTask: (token: string, id: string, new_datetime: string, reason?: string) =>
    req<RescheduleOptions>(`/tasks/${id}/reschedule`, token, {
      method: 'PATCH',
      body: JSON.stringify({ new_datetime, reason }),
    }),
  saveContext: (token: string, id: string, raw_brain_dump: string) =>
    req<{ breadcrumb: string; task_id: string }>(`/tasks/${id}/context-save`, token, {
      method: 'POST',
      body: JSON.stringify({ raw_brain_dump }),
    }),
  getContext: (token: string, id: string) =>
    req<{ breadcrumb: string | null; saved_at?: string }>(`/tasks/${id}/context-save`, token),

  getCascade: (token: string, id: string) =>
    req<any>(`/tasks/${id}/cascade`, token),
  getClusters: (token: string) =>
    req<{ clusters: Cluster[]; total_tasks: number }>('/tasks/clusters', token),
  getNextSession: (token: string) =>
    req<{ cluster: Cluster | null; message?: string }>('/tasks/next-session', token),

  // Agents
  getMorningBrief: (token: string) =>
    req<{ brief: string }>('/agents/me/morning-brief', token, { method: 'POST' }),
  checkProcrastination: (token: string) =>
    req<{ diagnoses: any[] }>('/agents/me/procrastination-check', token, { method: 'POST' }),
  procrastinationForTask: (token: string, id: string) =>
    req<any>(`/agents/me/tasks/${id}/procrastination`, token, { method: 'POST' }),
  runBacklogAudit: (token: string) =>
    req<any>('/agents/me/backlog-audit', token, { method: 'POST' }),
  getResequence: (token: string) =>
    req<{ plans: any[]; overdue_count: number }>('/agents/me/resequence', token, { method: 'POST' }),

  // Schedule
  getEnergyWindows: (token: string) =>
    req<{ windows: EnergyWindow[]; hours_shown: number }>('/schedule/energy-windows', token),
  getOptimizedSchedule: (token: string) =>
    req<any>('/schedule/optimize', token),

  // Calendar
  getVacationFinder: (token: string) =>
    req<any>('/calendar/vacation-finder', token),

  // Users
  getMe: (token: string) =>
    req<any>('/users/me', token),
  getStreak: (token: string) =>
    req<any>('/users/me/streak', token),
  declareRecoveryDay: (token: string) =>
    req<any>('/users/me/recovery-day', token, { method: 'POST' }),
  getPlanningAccuracy: (token: string) =>
    req<any[]>('/users/me/planning-accuracy', token),
  getPlanningSummary: (token: string) =>
    req<{ overall_inflation: number | null; sample_count: number; per_skill: Record<string, any> }>('/users/me/planning-summary', token),

  // Voice
  transcribeAndCreate: (token: string, formData: FormData) =>
    fetch(`${BASE}/voice/transcribe-and-create`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    }).then(r => r.json()),
}
