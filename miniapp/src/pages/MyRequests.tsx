import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyRequests } from '../api/client'
import type { Request } from '../api/client'
import { Loader } from '../components/Loader'
import { PriorityBadge, STATUS_DOT_COLOR, StatusBadge } from '../components/StatusBadge'

const STATUS_FILTERS = [
  { key: '', label: 'Все' },
  { key: 'in_progress', label: 'В работе' },
  { key: 'resolved', label: 'Решенные' },
  { key: 'new', label: 'Новые' },
]

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин назад`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч назад`
  return `${Math.floor(hrs / 24)} д назад`
}

export default function MyRequests() {
  const [requests, setRequests] = useState<Request[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    const params = statusFilter ? { status: statusFilter } : undefined
    getMyRequests(params)
      .then((data) => setRequests(data.items ?? data ?? []))
      .catch(() => setRequests([]))
      .finally(() => setLoading(false))
  }, [statusFilter])

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Мои задачи</div>
          <div className="section-subtitle" style={{ marginBottom: 12 }}>
            Здесь только то, что уже ушло в работу и назначено вам. Если ничего нет, значит поток пока не требовал отдельной задачи.
          </div>
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto' }} className="scrollbar-hide">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.key}
                onClick={() => setStatusFilter(filter.key)}
                className={`filter-chip ${statusFilter === filter.key ? 'active' : ''}`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : requests.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card" style={{ textAlign: 'center', padding: '56px 22px', color: 'var(--text-soft)' }}>
            <div style={{ fontSize: 44, marginBottom: 10 }}>✅</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-main)' }}>Личных задач сейчас нет</div>
            <div style={{ fontSize: 13, lineHeight: 1.45, marginTop: 8 }}>
              Это нормально: сообщения и ситуации продолжают собираться в потоке, но лично вам пока ничего не назначено.
            </div>
          </div>
        </div>
      ) : (
        <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {requests.map((req) => (
            <Link key={req.id} to={`/requests/${req.id}`} style={{ textDecoration: 'none' }}>
              <div className="glass-card" style={{ padding: '14px 15px', borderLeft: `4px solid ${STATUS_DOT_COLOR[req.status] ?? '#cbd5e1'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 7 }}>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-soft)' }}>{req.ticket_number}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {req.sla_breached && <span style={{ fontSize: 11, color: '#ef4444', fontWeight: 700 }}>SLA</span>}
                    <StatusBadge status={req.status} showDot />
                  </div>
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.4, marginBottom: 8, color: 'var(--text-main)' }}>
                  {req.subject || req.body}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <PriorityBadge priority={req.priority} />
                  {req.department_name && (
                    <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>{req.department_name}</span>
                  )}
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-soft)' }}>{timeAgo(req.created_at)}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
