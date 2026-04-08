import { useEffect, useState, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getRequests, getDepartments } from '../api/client'
import type { Request, Department } from '../api/client'
import { StatusBadge, PriorityBadge, STATUS_DOT_COLOR } from '../components/StatusBadge'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'

const FILTERS = [
  { key: '',           label: 'Все' },
  { key: 'new',        label: '🆕 Новые' },
  { key: 'in_progress',label: '🟡 В работе' },
  { key: 'resolved',   label: '✅ Решённые' },
  { key: 'sla',        label: '⚠️ SLA' },
]

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч`
  return `${Math.floor(hrs / 24)} д`
}

export default function RequestList() {
  const [requests, setRequests] = useState<Request[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [departments, setDepartments] = useState<Department[]>([])
  const [deptFilter, setDeptFilter] = useState<number | null>(null)

  useEffect(() => {
    getDepartments().then(setDepartments).catch(() => {})
  }, [])

  const statusFilter = searchParams.get('status') ?? ''
  const slaFilter = searchParams.get('sla_breached') === 'true'
  const assignedToMe = searchParams.get('assigned_to_me') === 'true'

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setDebouncedSearch(search), 400)
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current) }
  }, [search])

  const buildParams = (p: number) => {
    const params: Record<string, string | number> = { page: p, page_size: 20 }
    if (statusFilter) params.status = statusFilter
    if (slaFilter) params.sla_breached = 'true'
    if (assignedToMe) params.assigned_to_me = 'true'
    if (debouncedSearch) params.search = debouncedSearch
    if (deptFilter) params.department_id = deptFilter
    return params
  }

  useEffect(() => {
    setPage(1)
    setLoading(true)
    getRequests(buildParams(1))
      .then(d => { setRequests(d.items ?? []); setTotal(d.total ?? 0) })
      .catch(() => setRequests([]))
      .finally(() => setLoading(false))
  }, [statusFilter, slaFilter, assignedToMe, debouncedSearch, deptFilter])

  const loadMore = async () => {
    const nextPage = page + 1
    setLoadingMore(true)
    try {
      const d = await getRequests(buildParams(nextPage))
      setRequests(prev => [...prev, ...(d.items ?? [])])
      setPage(nextPage)
    } finally { setLoadingMore(false) }
  }

  const setFilter = (key: string) => {
    haptic.select()
    if (key === 'sla') {
      setSearchParams({ sla_breached: 'true' })
    } else if (key === '') {
      setSearchParams({})
    } else {
      setSearchParams({ status: key })
    }
  }

  const activeFilter = slaFilter ? 'sla' : (statusFilter || '')

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Sticky header */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: 'var(--tg-theme-bg-color, #fff)',
        padding: '12px 12px 0',
        boxShadow: '0 1px 8px rgba(0,0,0,0.06)',
      }}>
        {/* Search */}
        <div style={{ position: 'relative', marginBottom: 10 }}>
          <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', fontSize: 16, pointerEvents: 'none' }}>🔍</span>
          <input
            type="search"
            placeholder="Поиск по номеру или тексту..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '10px 12px 10px 36px', borderRadius: 12,
              border: '1.5px solid rgba(0,0,0,0.1)', fontSize: 14, outline: 'none',
              background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
              color: 'var(--tg-theme-text-color, #000)',
            }}
          />
        </div>

        {/* Status filter chips */}
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 6 }} className="scrollbar-hide">
          {FILTERS.map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)} style={{
              flexShrink: 0, padding: '5px 12px', borderRadius: 100, fontSize: 13, fontWeight: 500,
              border: 'none', cursor: 'pointer',
              background: activeFilter === f.key ? '#2481cc' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
              color: activeFilter === f.key ? '#fff' : 'var(--tg-theme-text-color, #555)',
              transition: 'all 0.15s',
            }}>
              {f.label}
            </button>
          ))}
          {assignedToMe && (
            <button onClick={() => setSearchParams({})} style={{
              flexShrink: 0, padding: '5px 12px', borderRadius: 100, fontSize: 13,
              border: 'none', cursor: 'pointer', background: '#7c3aed', color: '#fff',
            }}>
              🎯 Мои
            </button>
          )}
        </div>

        {/* Department filter chips */}
        {departments.length > 0 && (
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 10 }} className="scrollbar-hide">
            <button onClick={() => { haptic.select(); setDeptFilter(null) }} style={{
              flexShrink: 0, padding: '4px 11px', borderRadius: 100, fontSize: 12, fontWeight: 500,
              border: 'none', cursor: 'pointer',
              background: deptFilter === null ? '#0f766e' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
              color: deptFilter === null ? '#fff' : 'var(--tg-theme-hint-color, #999)',
            }}>
              Все отделы
            </button>
            {departments.map(d => (
              <button key={d.id} onClick={() => { haptic.select(); setDeptFilter(d.id) }} style={{
                flexShrink: 0, padding: '4px 11px', borderRadius: 100, fontSize: 12, fontWeight: 500,
                border: 'none', cursor: 'pointer',
                background: deptFilter === d.id ? '#0f766e' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
                color: deptFilter === d.id ? '#fff' : 'var(--tg-theme-hint-color, #999)',
              }}>
                {d.icon_emoji ? `${d.icon_emoji} ${d.name}` : d.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Count info */}
      {!loading && (
        <div style={{ padding: '8px 16px', fontSize: 12, color: '#999' }}>
          {total > 0 ? `${requests.length} из ${total} заявок` : 'Заявок нет'}
        </div>
      )}

      {/* List */}
      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : requests.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 15 }}>Заявок не найдено</div>
          {(statusFilter || slaFilter) && (
            <button onClick={() => setSearchParams({})} style={{
              marginTop: 12, padding: '8px 20px', borderRadius: 100, border: 'none',
              background: '#2481cc', color: '#fff', fontSize: 14, cursor: 'pointer',
            }}>
              Сбросить фильтры
            </button>
          )}
        </div>
      ) : (
        <div style={{ padding: '4px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {requests.map(req => (
            <Link key={req.id} to={`/requests/${req.id}`} style={{ textDecoration: 'none' }}>
              <div style={{
                background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                borderRadius: 14, padding: '12px 14px',
                borderLeft: `4px solid ${STATUS_DOT_COLOR[req.status] ?? '#ddd'}`,
                position: 'relative',
              }}>
                {req.sla_breached && (
                  <div style={{ position: 'absolute', top: 10, right: 12, fontSize: 11, color: '#ef4444', fontWeight: 600 }}>⚠️ SLA</div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#999' }}>{req.ticket_number}</span>
                  <StatusBadge status={req.status} />
                </div>
                <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 6, paddingRight: req.sla_breached ? 50 : 0, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {req.subject || req.body}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <PriorityBadge priority={req.priority} />
                  {req.department_name && (
                    <span style={{ fontSize: 11, color: '#999', background: 'rgba(0,0,0,0.05)', padding: '2px 7px', borderRadius: 100 }}>
                      {req.department_name}
                    </span>
                  )}
                  {req.assigned_to_name && (
                    <span style={{ fontSize: 11, color: '#6b7280' }}>👤 {req.assigned_to_name}</span>
                  )}
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: '#bbb' }}>{timeAgo(req.created_at)}</span>
                </div>
                {req.ai_category && (
                  <div style={{ marginTop: 6, display: 'inline-flex', alignItems: 'center', gap: 4, background: '#f0f9ff', color: '#0369a1', borderRadius: 100, padding: '2px 8px', fontSize: 11 }}>
                    🤖 {req.ai_category}
                  </div>
                )}
              </div>
            </Link>
          ))}

          {requests.length < total && (
            <button
              onClick={loadMore}
              disabled={loadingMore}
              style={{
                width: '100%', padding: '12px', borderRadius: 12, border: 'none',
                background: 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
                color: '#2481cc', fontSize: 14, fontWeight: 500, cursor: 'pointer',
                marginBottom: 4,
              }}
            >
              {loadingMore ? 'Загрузка...' : `Загрузить ещё (${total - requests.length})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
