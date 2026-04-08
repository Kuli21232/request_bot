import axios from 'axios'
import WebApp from '../telegram'

const API_URL = import.meta.env.VITE_API_URL || 'https://bot-api.24beershop.ru'

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      try {
        const res = await axios.post(`${API_URL}/api/v1/auth/telegram`, { init_data: WebApp.initData })
        const token = res.data.access_token ?? res.data.token
        if (token) {
          localStorage.setItem('jwt_token', token)
          error.config.headers.Authorization = `Bearer ${token}`
          return axios(error.config)
        }
      } catch { localStorage.removeItem('jwt_token') }
    }
    return Promise.reject(error)
  }
)

export interface Request {
  id: number
  ticket_number: string
  subject?: string
  body: string
  status: string
  priority: string
  department_id?: number
  department_name?: string
  submitter_id?: number
  submitter_name?: string
  assigned_to_id?: number
  assigned_to_name?: string
  sla_deadline?: string
  sla_breached: boolean
  is_duplicate?: boolean
  ai_category?: string
  ai_sentiment?: string
  ai_subject?: string
  satisfaction_score?: number
  created_at: string
  updated_at?: string
}

export interface RequestDetail extends Request {
  attachments?: any[]
  comments: Comment[]
  history?: HistoryItem[]
  current_user_role?: string
  resolved_at?: string
  first_response_at?: string
}

export interface Comment {
  id: number
  body: string
  is_internal: boolean
  is_system?: boolean
  author?: string
  author_id?: number
  created_at: string
}

export interface HistoryItem {
  action: string
  field_name?: string
  old_value?: string
  new_value?: string
  created_at: string
}

export interface Stats {
  role: string
  total: number
  new: number
  open: number
  in_progress: number
  waiting_for_user: number
  resolved: number
  closed: number
  sla_breached: number
  avg_satisfaction?: number
}

export interface Department {
  id: number
  name: string
  icon_emoji?: string
  description?: string
  sla_hours?: number
}

export interface Agent {
  id: number
  first_name: string
  username?: string
  role: string
}

export interface VolumePoint {
  day: string
  count: number
}

// ── Auth ──────────────────────────────────────────────────────
export const authTelegram = async (initData: string): Promise<{ access_token: string }> => {
  const res = await axios.post(`${API_URL}/api/v1/auth/telegram`, { init_data: initData })
  const token = res.data.access_token ?? res.data.token
  return { access_token: token }
}

// ── Requests ──────────────────────────────────────────────────
export const getRequests = async (params?: Record<string, string | number>) => {
  const res = await api.get('/api/v1/requests', { params })
  return res.data
}

export const getRequest = async (id: number): Promise<RequestDetail> => {
  const res = await api.get(`/api/v1/requests/${id}`)
  return res.data
}

export const getMyRequests = async (params?: Record<string, string>) => {
  const res = await api.get('/api/v1/requests', { params: { my: 'true', ...params } })
  return res.data
}

export const updateStatus = async (id: number, status: string) => {
  const res = await api.patch(`/api/v1/requests/${id}/status`, { status })
  return res.data
}

export const updatePriority = async (id: number, priority: string) => {
  const res = await api.patch(`/api/v1/requests/${id}/priority`, { priority })
  return res.data
}

export const assignRequest = async (id: number, agentId: number) => {
  const res = await api.post(`/api/v1/requests/${id}/assign`, { agent_id: agentId })
  return res.data
}

export const addComment = async (id: number, body: string, isInternal = false) => {
  const res = await api.post(`/api/v1/requests/${id}/comments`, { body, is_internal: isInternal })
  return res.data
}

export const rateRequest = async (id: number, score: number, comment?: string) => {
  const res = await api.post(`/api/v1/requests/${id}/rate`, { score, comment })
  return res.data
}

export const getHistory = async (id: number): Promise<HistoryItem[]> => {
  const res = await api.get(`/api/v1/requests/${id}/history`)
  return res.data
}

// ── Analytics ─────────────────────────────────────────────────
export const getMyStats = async (): Promise<Stats> => {
  const res = await api.get('/api/v1/analytics/my-stats')
  return res.data
}

export const getOverview = async (): Promise<Stats & { avg_satisfaction: number }> => {
  const res = await api.get('/api/v1/analytics/overview')
  return res.data
}

export const getVolume = async (days = 7): Promise<VolumePoint[]> => {
  const res = await api.get('/api/v1/analytics/volume', { params: { days } })
  return res.data
}

export const getByDepartment = async () => {
  const res = await api.get('/api/v1/analytics/by-department')
  return res.data
}

export const getSlaStats = async () => {
  const res = await api.get('/api/v1/analytics/sla')
  return res.data
}

// ── Departments & Users ────────────────────────────────────────
export const getDepartments = async (): Promise<Department[]> => {
  const res = await api.get('/api/v1/departments')
  return res.data
}

export const getAgents = async (): Promise<Agent[]> => {
  const res = await api.get('/api/v1/users', { params: { role: 'agent,supervisor,admin' } })
  return res.data ?? []
}

export default api
