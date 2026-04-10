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
      } catch {
        localStorage.removeItem('jwt_token')
      }
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

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
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
  case_key?: string
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
  submitter_id?: number
  submitter_name?: string
  submitter_username?: string
  responsible_user_id?: number
  responsible_user_name?: string
  suggested_owner_id?: number
  suggested_owner_name?: string
  source_topic_id?: number
  source_message_id?: number
  source_chat_id?: number
  happened_at: string
}

export interface FlowMediaItem {
  id: number
  kind: string
  mime_type?: string
  file_name?: string
  original_size?: number
  compressed_size?: number
  width?: number
  height?: number
  duration_seconds?: number
  preview_url?: string
  content_url?: string
  has_preview?: boolean
  can_open_content?: boolean
  topic_id?: number
  topic_title?: string
  group_title?: string
  signal_id?: number
  signal_summary?: string
  happened_at?: string
}

export interface FlowSignalDetail extends FlowSignal {
  attachments?: any[]
  entities?: Record<string, any>
  ai_labels?: Record<string, any>
  media_flags?: Record<string, any>
  media?: FlowMediaItem[]
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
  primary_topic_id?: number
  primary_topic_title?: string
  request_id?: number
  request_ticket?: string
  responsible_user_id?: number
  responsible_user_name?: string
  responsible_user_username?: string
  assigned_by_user_id?: number
  assigned_by_user_name?: string
  assigned_at?: string
  suggested_owner_id?: number
  suggested_owner_name?: string
  last_signal_at?: string
  updated_at?: string
}

export interface FlowCaseDetail extends FlowCase {
  owners?: string[]
  ai_labels?: Record<string, any>
  signals?: FlowSignal[]
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
  automation?: TopicAutomation
}

export interface Topic {
  id: number
  group_id: number
  group_title?: string
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

export interface TopicAutomation {
  priority?: string
  recommended_action?: string
  summary?: string
  attention_count?: number
  open_case_count?: number
  critical_case_count?: number
  follow_up_needed?: boolean
  dominant_kind?: string
  top_stores?: string[]
  signal_examples?: string[]
  case_titles?: string[]
  last_signal_at?: string
}

export interface ActionBoardItem {
  topic_id: number
  topic_title: string
  group_id?: number
  group_title?: string
  priority: string
  recommended_action: string
  summary?: string
  attention_count: number
  open_case_count: number
  critical_case_count: number
  follow_up_needed: boolean
  last_signal_at?: string
  score: number
}

export interface GroupDigestTopic {
  topic_id: number
  topic_title: string
  priority: string
  recommended_action?: string
  summary?: string
}

export interface GroupDigest {
  group_id?: number
  group_title: string
  signal_count: number
  attention_count: number
  critical_case_count: number
  open_case_count: number
  follow_up_topics: number
  recommended_focus: string
  top_topics: GroupDigestTopic[]
}

export interface TopicSection {
  topic_id: number
  topic_title: string
  group_id: number
  group_title?: string
  icon_emoji?: string
  topic_kind: string
  priority: string
  score: number
  reasons: string[]
  stats: {
    signal_count: number
    attention_count: number
    media_signal_count: number
    critical_case_count: number
    open_case_count: number
    last_signal_at?: string
    message_count: number
    media_count: number
  }
  profile_summary?: string
  automation?: TopicAutomation
  signals: FlowSignal[]
  cases: FlowCase[]
}

export interface ProfileNote {
  id: number
  body: string
  notify_target: boolean
  author_id?: number
  author_name?: string
  created_at?: string
}

export interface TeamUser {
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
  notes_count?: number
  notes?: ProfileNote[]
  is_watching?: boolean
  watchers_count?: number
  assigned_open_case_count?: number
  critical_case_count?: number
  submitted_signal_count?: number
  ai_summary?: string
  top_topics?: { topic_title: string; count: number; attention_count?: number }[]
}

export interface UserTopicActivityItem {
  id: number
  kind: string
  importance: string
  summary?: string
  body: string
  store?: string
  topic_id?: number
  topic_title?: string
  case_id?: number
  case_title?: string
  request_id?: number
  request_ticket?: string
  has_media: boolean
  requires_attention: boolean
  happened_at: string
  media?: FlowMediaItem[]
}

export interface UserTopicGroup {
  topic_id?: number
  topic_title: string
  group_title?: string
  signal_count: number
  request_count: number
  case_count: number
  media_count: number
  requires_attention_count: number
  last_activity_at?: string
  items: UserTopicActivityItem[]
}

export interface TeamProfile extends TeamUser {
  assigned_cases: FlowCase[]
  topic_groups: UserTopicGroup[]
  media_items: FlowMediaItem[]
  ai_summary?: string
  ai_recommendations?: string[]
  ai_snapshot?: {
    summary?: string
    dominant_topics?: { topic_title: string; count: number; attention_count?: number }[]
    assigned_case_stats?: Record<string, number>
    recommendations?: string[]
    analysis?: Record<string, any>
    last_analyzed_at?: string
  } | null
  permissions: {
    is_self: boolean
    can_view_team: boolean
    can_view_internal_notes: boolean
    can_assign_responsible: boolean
  }
}

export const authTelegram = async (initData: string): Promise<{ access_token: string }> => {
  const res = await axios.post(`${API_URL}/api/v1/auth/telegram`, { init_data: initData })
  const token = res.data.access_token ?? res.data.token
  return { access_token: token }
}

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

export const getSignals = async (params?: Record<string, string | number | boolean>) => {
  const res = await api.get<PaginatedResponse<FlowSignal>>('/api/v1/flow/signals', { params })
  return res.data
}

export const getSignal = async (id: number): Promise<FlowSignalDetail> => {
  const res = await api.get(`/api/v1/flow/signals/${id}`)
  return res.data
}

export const getCases = async (params?: Record<string, string | number | boolean>) => {
  const res = await api.get<PaginatedResponse<FlowCase>>('/api/v1/flow/cases', { params })
  return res.data
}

export const getCase = async (id: number): Promise<FlowCaseDetail> => {
  const res = await api.get(`/api/v1/flow/cases/${id}`)
  return res.data
}

export const assignCaseResponsible = async (id: number, userId?: number | null) => {
  const res = await api.patch(`/api/v1/flow/cases/${id}/responsible`, { user_id: userId ?? null })
  return res.data
}

export const getDigestOverview = async () => {
  const res = await api.get('/api/v1/flow/digests/overview')
  return res.data
}

export const getTopicSections = async (params?: Record<string, string | number | boolean>) => {
  const res = await api.get<{ items: TopicSection[]; total: number }>('/api/v1/flow/topic-sections', { params })
  return res.data
}

export const getActionBoard = async (params?: Record<string, string | number | boolean>) => {
  const res = await api.get<{ items: ActionBoardItem[]; total: number }>('/api/v1/flow/action-board', { params })
  return res.data
}

export const getGroupDigests = async (params?: Record<string, string | number | boolean>) => {
  const res = await api.get<{ items: GroupDigest[]; total: number }>('/api/v1/flow/group-digests', { params })
  return res.data
}

export const getTopics = async (): Promise<Topic[]> => {
  const res = await api.get('/api/v1/topics')
  return res.data
}

export const getDepartments = async (): Promise<Department[]> => {
  const res = await api.get('/api/v1/departments')
  return res.data
}

export const getAgents = async (): Promise<Agent[]> => {
  const res = await api.get('/api/v1/users', { params: { role: 'agent,supervisor,admin' } })
  return res.data ?? []
}

export const getTeamUsers = async (params?: Record<string, string | number>) => {
  const res = await api.get<TeamUser[]>('/api/v1/users', { params })
  return res.data ?? []
}

export const getTeamUser = async (id: number): Promise<TeamUser> => {
  const res = await api.get(`/api/v1/users/${id}`)
  return res.data
}

export const getMyProfile = async (): Promise<TeamProfile> => {
  const res = await api.get('/api/v1/users/profile')
  return res.data
}

export const getUserProfile = async (id: number): Promise<TeamProfile> => {
  const res = await api.get(`/api/v1/users/${id}/profile`)
  return res.data
}

export const addProfileNote = async (id: number, body: string, notifyTarget = false): Promise<ProfileNote> => {
  const res = await api.post(`/api/v1/users/${id}/notes`, { body, notify_target: notifyTarget })
  return res.data
}

export const watchProfile = async (id: number) => {
  const res = await api.post(`/api/v1/users/${id}/watch`)
  return res.data
}

export const unwatchProfile = async (id: number) => {
  const res = await api.delete(`/api/v1/users/${id}/watch`)
  return res.data
}

export const resolveApiUrl = (path?: string | null) => {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  return `${API_URL}${path}`
}

export default api
