import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'https://bot-api.24beershop.ru'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('auth_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export type RequestStatus =
  | 'new'
  | 'open'
  | 'in_progress'
  | 'waiting_for_user'
  | 'resolved'
  | 'closed'

export type RequestPriority = 'low' | 'normal' | 'high' | 'critical'

export interface User {
  id: number
  email: string
  name: string
  username?: string
  role: string
  department_id?: number
}

export interface Department {
  id: number
  name: string
  emoji?: string
}

export interface Request {
  id: number
  ticket_number: string
  subject?: string
  body: string
  status: RequestStatus
  priority: RequestPriority
  department_id?: number
  department_name?: string
  submitter_id?: number
  submitter_name?: string
  assigned_to_id?: number
  assigned_to_name?: string
  sla_deadline?: string
  sla_breached?: boolean
  ai_category?: string
  ai_sentiment?: string
  satisfaction_score?: number
  created_at: string
  updated_at?: string
}

export interface Comment {
  id: number
  body: string
  author?: string
  author_id?: number
  is_internal: boolean
  is_system?: boolean
  created_at: string
}

export interface HistoryEntry {
  action: string
  field_name?: string
  old_value?: string
  new_value?: string
  created_at: string
}

export interface RequestDetail extends Request {
  attachments?: any[]
  current_user_role?: string
  first_response_at?: string
  resolved_at?: string
  comments: Comment[]
  history: HistoryEntry[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AnalyticsOverview {
  total: number
  new: number
  in_progress: number
  resolved: number
  sla_breached: number
  avg_satisfaction?: number
}

export interface VolumeDay {
  day: string
  count: number
}

export interface DepartmentStat {
  department: string
  emoji?: string
  count: number
}

export interface SlaStat {
  compliance_percent: number
  breached: number
  on_time: number
  total_with_sla: number
}

export interface AgentStat {
  name: string
  username: string
  open_count: number
}

export interface MyStats {
  total_assigned: number
  resolved_today: number
  avg_response_time?: number
  open_requests: number
}

export interface FlowSignal {
  id: number
  kind: string
  importance: string
  actionability: string
  summary?: string
  body: string
  store?: string
  topic_label?: string
  recommended_action?: string
  has_media: boolean
  requires_attention: boolean
  is_noise: boolean
  digest_bucket?: string
  ai_confidence?: number
  case_id?: number
  case_title?: string
  department_id?: number
  department_name?: string
  request_id?: number
  request_ticket?: string
  happened_at: string
}

export interface FlowCase {
  id: number
  title: string
  summary?: string
  status: string
  priority: string
  kind: string
  signal_count: number
  media_count: number
  is_critical: boolean
  stores_affected: string[]
  recommended_action?: string
  ai_confidence?: number
  department_id?: number
  department_name?: string
  request_id?: number
  request_ticket?: string
  last_signal_at?: string
  updated_at?: string
}

export interface DigestOverview {
  total_signals: number
  requires_attention: number
  with_media: number
  noise: number
  critical_cases: number
  top_kinds: Array<{ kind: string; count: number }>
}

export interface TopicProfile {
  preferred_department_id?: number
  profile_summary?: string
  allowed_signal_types: string[]
  default_actions: Record<string, string>
  priority_rules: Record<string, any>
  media_policy: Record<string, any>
  confidence_threshold: number
  auto_learn_enabled: boolean
  system_prompt?: string
  examples?: any[]
  behavior_rules?: Record<string, any>
  learning_snapshot?: Record<string, any>
}

export interface Topic {
  id: number
  group_id: number
  telegram_topic_id: number
  title: string
  icon_emoji?: string
  topic_kind: string
  is_active: boolean
  message_count: number
  media_count: number
  signal_count: number
  last_seen_at?: string
  profile_version: number
  profile?: TopicProfile
}

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<{ token: string; user: User }>('/api/v1/auth/login', { email, password }),
}

export interface RequestsParams {
  status?: string
  search?: string
  page?: number
  page_size?: number
  department_id?: number
  assigned_to_me?: boolean
}

export const requestsApi = {
  list: (params: RequestsParams = {}) =>
    apiClient.get<PaginatedResponse<Request>>('/api/v1/requests', { params }),
  get: (id: number) =>
    apiClient.get<RequestDetail>(`/api/v1/requests/${id}`),
  changeStatus: (id: number, status: RequestStatus) =>
    apiClient.patch(`/api/v1/requests/${id}/status`, { status }),
  changePriority: (id: number, priority: RequestPriority) =>
    apiClient.patch(`/api/v1/requests/${id}/priority`, { priority }),
  assign: (id: number, agent_id: number) =>
    apiClient.post(`/api/v1/requests/${id}/assign`, { agent_id }),
  addComment: (id: number, body: string, is_internal = false) =>
    apiClient.post<Comment>(`/api/v1/requests/${id}/comments`, { body, is_internal }),
}

export const analyticsApi = {
  overview: () =>
    apiClient.get<AnalyticsOverview>('/api/v1/analytics/overview'),
  volume: (days = 30) =>
    apiClient.get<VolumeDay[]>('/api/v1/analytics/volume', { params: { days } }),
  byDepartment: () =>
    apiClient.get<DepartmentStat[]>('/api/v1/analytics/by-department'),
  sla: () =>
    apiClient.get<SlaStat>('/api/v1/analytics/sla'),
  agents: () =>
    apiClient.get<AgentStat[]>('/api/v1/analytics/agents'),
  myStats: () =>
    apiClient.get<MyStats>('/api/v1/analytics/my-stats'),
}

export interface FlowParams {
  page?: number
  page_size?: number
  kind?: string
  importance?: string
  status?: string
  search?: string
  requires_attention?: boolean
}

export const flowApi = {
  listSignals: (params: FlowParams = {}) =>
    apiClient.get<PaginatedResponse<FlowSignal>>('/api/v1/flow/signals', { params }),
  getSignal: (id: number) =>
    apiClient.get<FlowSignal>(`/api/v1/flow/signals/${id}`),
  listCases: (params: FlowParams = {}) =>
    apiClient.get<PaginatedResponse<FlowCase>>('/api/v1/flow/cases', { params }),
  getCase: (id: number) =>
    apiClient.get<FlowCase>(`/api/v1/flow/cases/${id}`),
  changeCaseStatus: (id: number, status: string) =>
    apiClient.patch(`/api/v1/flow/cases/${id}/status`, { status }),
  digestOverview: () =>
    apiClient.get<DigestOverview>('/api/v1/flow/digests/overview'),
}

export const departmentsApi = {
  list: () =>
    apiClient.get<Department[]>('/api/v1/departments'),
}

export const topicsApi = {
  list: () =>
    apiClient.get<Topic[]>('/api/v1/topics'),
  get: (id: number) =>
    apiClient.get<Topic>(`/api/v1/topics/${id}`),
  updateProfile: (id: number, payload: Partial<TopicProfile>) =>
    apiClient.patch<Topic>(`/api/v1/topics/${id}/profile`, payload),
}

export interface AdminUser {
  id: number
  telegram_user_id?: number
  first_name: string
  last_name?: string
  username?: string
  email?: string
  role: string
  is_banned: boolean
  last_active_at?: string
  created_at?: string
}

export const usersApi = {
  list: (params?: { role?: string; search?: string; page?: number }) =>
    apiClient.get<AdminUser[]>('/api/v1/users', { params }),
  me: () =>
    apiClient.get<AdminUser>('/api/v1/users/me'),
  updateRole: (id: number, role: string) =>
    apiClient.patch<AdminUser>(`/api/v1/users/${id}/role`, { role }),
  toggleBan: (id: number, is_banned: boolean) =>
    apiClient.patch<AdminUser>(`/api/v1/users/${id}/ban`, { is_banned }),
}
