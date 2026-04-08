import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Send,
  Lock,
  Clock,
  User,
  Building2,
  AlertTriangle,
  Calendar,
  Hash,
  MessageSquare,
  History,
  ChevronDown,
} from 'lucide-react'
import { requestsApi, type RequestDetail as IRequestDetail, type RequestStatus, type RequestPriority, type Comment } from '../api/client'
import { StatusBadge, PriorityBadge, statusConfig, priorityConfig } from '../components/StatusBadge'
import { Loader } from '../components/Loader'

export function RequestDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [request, setRequest] = useState<IRequestDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [commentText, setCommentText] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [submittingComment, setSubmittingComment] = useState(false)
  const [activeTab, setActiveTab] = useState<'comments' | 'history'>('comments')
  const [statusDropdown, setStatusDropdown] = useState(false)
  const [priorityDropdown, setPriorityDropdown] = useState(false)
  const [changingStatus, setChangingStatus] = useState(false)
  const [changingPriority, setChangingPriority] = useState(false)

  const fetchDetail = useCallback(async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const { data } = await requestsApi.get(Number(id))
      setRequest(data)
    } catch {
      setRequest(null)
    } finally {
      setIsLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchDetail()
  }, [fetchDetail])

  const handleStatusChange = async (status: RequestStatus) => {
    if (!request) return
    setChangingStatus(true)
    setStatusDropdown(false)
    try {
      await requestsApi.changeStatus(request.id, status)
      setRequest((prev) => prev ? { ...prev, status } : prev)
    } finally {
      setChangingStatus(false)
    }
  }

  const handlePriorityChange = async (priority: RequestPriority) => {
    if (!request) return
    setChangingPriority(true)
    setPriorityDropdown(false)
    try {
      await requestsApi.changePriority(request.id, priority)
      setRequest((prev) => prev ? { ...prev, priority } : prev)
    } finally {
      setChangingPriority(false)
    }
  }

  const handleAddComment = async () => {
    if (!request || !commentText.trim()) return
    setSubmittingComment(true)
    try {
      const { data } = await requestsApi.addComment(request.id, commentText.trim(), isInternal)
      setRequest((prev) =>
        prev ? { ...prev, comments: [...(prev.comments || []), data] } : prev
      )
      setCommentText('')
    } finally {
      setSubmittingComment(false)
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  const formatSLA = (req: IRequestDetail) => {
    if (!req.sla_deadline) return null
    const deadline = new Date(req.sla_deadline)
    const now = new Date()
    const diff = deadline.getTime() - now.getTime()
    const overdue = diff < 0
    const hrs = Math.abs(Math.floor(diff / 3600000))
    const mins = Math.abs(Math.floor((diff % 3600000) / 60000))
    return {
      text: overdue ? `Просрочено на ${hrs}ч ${mins}м` : `Осталось ${hrs}ч ${mins}м`,
      overdue,
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" />
      </div>
    )
  }

  if (!request) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-400">
        <AlertTriangle className="w-10 h-10 mb-3 opacity-40" />
        <p className="text-base font-medium">Заявка не найдена</p>
        <button
          onClick={() => navigate('/requests')}
          className="mt-4 text-sm text-blue-500 hover:underline"
        >
          Вернуться к списку
        </button>
      </div>
    )
  }

  const sla = formatSLA(request)

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Back */}
      <button
        onClick={() => navigate('/requests')}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Назад к заявкам
      </button>

      {/* Header card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
        <div className="flex flex-wrap items-start gap-4 justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
              <Hash className="w-3.5 h-3.5" />
              <span>Заявка #{request.id}</span>
              <span>·</span>
              <Calendar className="w-3.5 h-3.5" />
              <span>{formatDate(request.created_at)}</span>
            </div>
            <h2 className="text-xl font-bold text-slate-800">{request.subject || request.body?.slice(0, 100)}</h2>
            {request.body && (
              <p className="text-slate-600 mt-2 text-sm leading-relaxed">{request.body}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Status dropdown */}
            <div className="relative">
              <button
                onClick={() => { setStatusDropdown((s) => !s); setPriorityDropdown(false) }}
                className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-sm hover:bg-slate-50 transition-colors"
              >
                {changingStatus ? <Loader size="sm" /> : <StatusBadge status={request.status} />}
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>
              {statusDropdown && (
                <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-40">
                  <p className="px-3 py-1 text-xs text-slate-400 font-medium uppercase">Изменить статус</p>
                  {(Object.keys(statusConfig) as RequestStatus[]).map((s) => (
                    <button
                      key={s}
                      onClick={() => handleStatusChange(s)}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2"
                    >
                      <StatusBadge status={s} small />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Priority dropdown */}
            <div className="relative">
              <button
                onClick={() => { setPriorityDropdown((s) => !s); setStatusDropdown(false) }}
                className="flex items-center gap-1.5 border border-slate-200 rounded-lg px-3 py-1.5 text-sm hover:bg-slate-50 transition-colors"
              >
                {changingPriority ? <Loader size="sm" /> : <PriorityBadge priority={request.priority} />}
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>
              {priorityDropdown && (
                <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-36">
                  <p className="px-3 py-1 text-xs text-slate-400 font-medium uppercase">Приоритет</p>
                  {(Object.keys(priorityConfig) as RequestPriority[]).map((p) => (
                    <button
                      key={p}
                      onClick={() => handlePriorityChange(p)}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2"
                    >
                      <PriorityBadge priority={p} small />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Meta */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 pt-5 border-t border-slate-100">
          <div>
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1">
              <Building2 className="w-3 h-3" /> Отдел
            </p>
            <p className="text-sm font-medium text-slate-700">
              {request.department_name || '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1">
              <User className="w-3 h-3" /> Исполнитель
            </p>
            <p className="text-sm font-medium text-slate-700">
              {request.assigned_to_name || 'Не назначен'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1">
              <User className="w-3 h-3" /> Автор
            </p>
            <p className="text-sm font-medium text-slate-700">
              {request.submitter_name || '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1">
              <Clock className="w-3 h-3" /> SLA
            </p>
            {sla ? (
              <p className={`text-sm font-medium ${sla.overdue ? 'text-red-600' : 'text-green-600'}`}>
                {sla.text}
              </p>
            ) : (
              <p className="text-sm text-slate-400">—</p>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="flex border-b border-slate-100">
          <button
            onClick={() => setActiveTab('comments')}
            className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'comments'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            Комментарии
            {request.comments?.length > 0 && (
              <span className="bg-slate-100 text-slate-600 text-xs rounded-full px-2 py-0.5">
                {request.comments.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'history'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <History className="w-4 h-4" />
            История
            {request.history?.length > 0 && (
              <span className="bg-slate-100 text-slate-600 text-xs rounded-full px-2 py-0.5">
                {request.history.length}
              </span>
            )}
          </button>
        </div>

        <div className="p-5">
          {activeTab === 'comments' && (
            <div className="space-y-4">
              {request.comments?.length === 0 && (
                <p className="text-slate-400 text-sm text-center py-4">Комментариев нет</p>
              )}
              {request.comments?.map((comment: Comment) => (
                <div
                  key={comment.id}
                  className={`rounded-xl p-4 ${
                    comment.is_internal
                      ? 'bg-amber-50 border border-amber-100'
                      : 'bg-slate-50 border border-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-blue-600 text-xs font-semibold">
                        {comment.author?.charAt(0)?.toUpperCase() || '?'}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-slate-700">{comment.author}</span>
                    {comment.is_internal && (
                      <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">
                        <Lock className="w-3 h-3" /> Внутренний
                      </span>
                    )}
                    <span className="text-xs text-slate-400 ml-auto">{formatDate(comment.created_at)}</span>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{comment.body}</p>
                </div>
              ))}

              {/* Add comment */}
              <div className="mt-5 pt-4 border-t border-slate-100">
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Напишите комментарий..."
                  rows={3}
                  className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
                <div className="flex items-center justify-between mt-2">
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={isInternal}
                      onChange={(e) => setIsInternal(e.target.checked)}
                      className="w-4 h-4 rounded border-slate-300 text-amber-500 focus:ring-amber-500"
                    />
                    <Lock className="w-3.5 h-3.5 text-amber-500" />
                    Внутренний комментарий
                  </label>
                  <button
                    onClick={handleAddComment}
                    disabled={!commentText.trim() || submittingComment}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    {submittingComment ? <Loader size="sm" /> : <Send className="w-4 h-4" />}
                    Отправить
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="space-y-3">
              {request.history?.length === 0 && (
                <p className="text-slate-400 text-sm text-center py-4">История пуста</p>
              )}
              {request.history?.map((entry, idx) => (
                <div key={idx} className="flex gap-3 items-start">
                  <div className="w-7 h-7 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <History className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm text-slate-500">{entry.action}</span>
                      {entry.old_value && entry.new_value && (
                        <>
                          <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{entry.old_value}</span>
                          <span className="text-slate-400 text-xs">→</span>
                          <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{entry.new_value}</span>
                        </>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{formatDate(entry.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
