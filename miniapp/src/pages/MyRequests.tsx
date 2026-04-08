import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyRequests } from '../api/client'
import type { Request } from '../api/client'
import { StatusBadge, PriorityBadge, STATUS_DOT_COLOR } from '../components/StatusBadge'
import { Loader } from '../components/Loader'

const STATUS_FILTERS = [
  { key: '', label: 'Все' },
  { key: 'in_progress', label: '🟡 В работе' },
  { key: 'resolved', label: '✅ Решённые' },
  { key: 'new', label: '🆕 Новые' },
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
      .then(d => setRequests(d.items ?? d ?? []))
      .catch(() => setRequests([]))
      .finally(() => setLoading(false))
  }, [statusFilter])

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #7c3aed, #9333ea)',
        padding: '24px 16px 20px',
      }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>👤 Мои заявки</div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', marginTop: 4 }}>
          {requests.length} заявок
        </div>
      </div>

      {/* Filters */}
      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, overflowX: 'auto' }} className="scrollbar-hide">
        {STATUS_FILTERS.map(f => (
          <button key={f.key} onClick={() => setStatusFilter(f.key)} style={{
            flexShrink: 0, padding: '5px 12px', borderRadius: 100, border: 'none', cursor: 'pointer',
            fontSize: 13, fontWeight: 500,
            background: statusFilter === f.key ? '#7c3aed' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
            color: statusFilter === f.key ? '#fff' : 'var(--tg-theme-text-color, #555)',
          }}>
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : requests.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 500 }}>Заявок нет</div>
          <div style={{ fontSize: 13, marginTop: 6 }}>
            Напишите в нужный топик группы, чтобы создать заявку
          </div>
        </div>
      ) : (
        <div style={{ padding: '4px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {requests.map(req => (
            <Link key={req.id} to={`/requests/${req.id}`} style={{ textDecoration: 'none' }}>
              <div style={{
                background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                borderRadius: 14, padding: '14px',
                borderLeft: `4px solid ${STATUS_DOT_COLOR[req.status] ?? '#ddd'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#999' }}>{req.ticket_number}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {req.sla_breached && <span style={{ fontSize: 11, color: '#ef4444' }}>⚠️ SLA</span>}
                    <StatusBadge status={req.status} showDot />
                  </div>
                </div>
                <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.4, marginBottom: 8, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {req.subject || req.body}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <PriorityBadge priority={req.priority} />
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: '#bbb' }}>
                    {timeAgo(req.created_at)}
                  </span>
                </div>
                {req.assigned_to_name && (
                  <div style={{ marginTop: 6, fontSize: 12, color: '#6b7280' }}>
                    👤 {req.assigned_to_name}
                  </div>
                )}
                {req.satisfaction_score && (
                  <div style={{ marginTop: 4, fontSize: 12, color: '#f59e0b' }}>
                    {'⭐'.repeat(req.satisfaction_score)} Вы оценили
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
