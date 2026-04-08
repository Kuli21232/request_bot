import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Calendar,
  User,
  Building2,
  ArrowUpDown,
} from 'lucide-react'
import { requestsApi, departmentsApi, type Request, type RequestStatus, type Department } from '../api/client'
import { StatusBadge, PriorityBadge, statusConfig } from '../components/StatusBadge'
import { Loader } from '../components/Loader'

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Все статусы' },
  { value: 'new', label: 'Новый' },
  { value: 'open', label: 'Открыт' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'waiting_for_user', label: 'Ожидание' },
  { value: 'resolved', label: 'Решён' },
  { value: 'closed', label: 'Закрыт' },
]

const PAGE_SIZE = 20

export function Requests() {
  const navigate = useNavigate()
  const [requests, setRequests] = useState<Request[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [departments, setDepartments] = useState<Department[]>([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [deptId, setDeptId] = useState<number | ''>('')
  const [slaBreached, setSlaBreached] = useState(false)
  const [assignedToMe, setAssignedToMe] = useState(false)
  const [changingStatus, setChangingStatus] = useState<number | null>(null)
  const [statusMenuFor, setStatusMenuFor] = useState<number | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const fetchRequests = useCallback(async () => {
    setIsLoading(true)
    try {
      const params: Record<string, string | number | boolean> = { page, page_size: PAGE_SIZE }
      if (search) params.search = search
      if (status) params.status = status
      if (deptId) params.department_id = deptId
      if (slaBreached) params.sla_breached = true
      if (assignedToMe) params.assigned_to_me = true
      const { data } = await requestsApi.list(params)
      setRequests(data.items || [])
      setTotal(data.total || 0)
    } catch {
      setRequests([])
    } finally {
      setIsLoading(false)
    }
  }, [page, search, status, deptId, slaBreached, assignedToMe])

  useEffect(() => {
    departmentsApi.list().then((r) => setDepartments(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setPage(1)
  }, [search, status, deptId, slaBreached, assignedToMe])

  useEffect(() => {
    fetchRequests()
  }, [fetchRequests])

  // Close status menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setStatusMenuFor(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleStatusChange = async (reqId: number, newStatus: RequestStatus) => {
    setChangingStatus(reqId)
    setStatusMenuFor(null)
    try {
      await requestsApi.changeStatus(reqId, newStatus)
      setRequests((prev) =>
        prev.map((r) => (r.id === reqId ? { ...r, status: newStatus } : r))
      )
    } catch {
      // ignore
    } finally {
      setChangingStatus(null)
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  const formatSLA = (req: Request) => {
    if (!req.sla_deadline) return null
    const deadline = new Date(req.sla_deadline)
    const now = new Date()
    const diff = deadline.getTime() - now.getTime()
    const overdue = diff < 0
    const hrs = Math.abs(Math.floor(diff / 3600000))
    const mins = Math.abs(Math.floor((diff % 3600000) / 60000))
    return {
      text: overdue ? `-${hrs}ч ${mins}м` : `${hrs}ч ${mins}м`,
      overdue,
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-4">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Search */}
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Поиск по теме..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Status */}
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {/* Department */}
          <select
            value={deptId}
            onChange={(e) => setDeptId(e.target.value ? Number(e.target.value) : '')}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
          >
            <option value="">Все отделы</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.emoji} {d.name}</option>
            ))}
          </select>

          {/* Toggles */}
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={slaBreached}
              onChange={(e) => setSlaBreached(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 text-red-500 focus:ring-red-500"
            />
            <AlertTriangle className="w-4 h-4 text-red-400" />
            SLA просрочен
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={assignedToMe}
              onChange={(e) => setAssignedToMe(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 text-blue-500 focus:ring-blue-500"
            />
            <User className="w-4 h-4 text-blue-400" />
            Мои заявки
          </label>

          <div className="flex items-center gap-1 text-xs text-slate-400 ml-auto">
            <Filter className="w-3.5 h-3.5" />
            {total} заявок
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader size="lg" />
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <Search className="w-10 h-10 mb-3 opacity-40" />
            <p className="text-base font-medium">Заявки не найдены</p>
            <p className="text-sm mt-1">Попробуйте изменить фильтры</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    <div className="flex items-center gap-1">
                      <ArrowUpDown className="w-3 h-3" /> №
                    </div>
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Тема</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Статус</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Приоритет</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    <div className="flex items-center gap-1"><Building2 className="w-3 h-3" /> Отдел</div>
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    <div className="flex items-center gap-1"><User className="w-3 h-3" /> Исполнитель</div>
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">SLA</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    <div className="flex items-center gap-1"><Calendar className="w-3 h-3" /> Дата</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => {
                  const sla = formatSLA(req)
                  return (
                    <tr
                      key={req.id}
                      onClick={() => navigate(`/requests/${req.id}`)}
                      className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        #{req.id}
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <p className="font-medium text-slate-800 truncate">{req.subject || req.body?.slice(0, 80)}</p>
                        {req.body && (
                          <p className="text-xs text-slate-400 truncate mt-0.5">{req.body}</p>
                        )}
                      </td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="relative inline-block" ref={statusMenuFor === req.id ? menuRef : undefined}>
                          {changingStatus === req.id ? (
                            <Loader size="sm" />
                          ) : (
                            <StatusBadge
                              status={req.status}
                              onClick={() => setStatusMenuFor(statusMenuFor === req.id ? null : req.id)}
                            />
                          )}
                          {statusMenuFor === req.id && (
                            <div className="absolute top-full left-0 mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-36">
                              {(Object.keys(statusConfig) as RequestStatus[]).map((s) => (
                                <button
                                  key={s}
                                  onClick={() => handleStatusChange(req.id, s)}
                                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2"
                                >
                                  <StatusBadge status={s} small />
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <PriorityBadge priority={req.priority} />
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">
                        {req.department_name ? (
                          <span>{req.department_name}</span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {req.assigned_to_name ? (
                          <div className="flex items-center gap-1.5">
                            <div className="w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center flex-shrink-0">
                              <span className="text-slate-500 text-xs">{req.assigned_to_name.charAt(0)}</span>
                            </div>
                            <span className="truncate max-w-24">{req.assigned_to_name}</span>
                          </div>
                        ) : (
                          <span className="text-slate-300">Не назначен</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {sla ? (
                          <span className={`text-xs font-mono ${sla.overdue ? 'text-red-500 font-semibold' : 'text-green-600'}`}>
                            {sla.text}
                          </span>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">
                        {formatDate(req.created_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
            <p className="text-xs text-slate-500">
              Показано {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} из {total}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                let pageNum: number
                if (totalPages <= 7) {
                  pageNum = i + 1
                } else if (page <= 4) {
                  pageNum = i + 1
                } else if (page >= totalPages - 3) {
                  pageNum = totalPages - 6 + i
                } else {
                  pageNum = page - 3 + i
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`w-7 h-7 rounded-lg text-xs font-medium transition-colors ${
                      pageNum === page
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
