import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCases, type FlowCase } from '../api/client'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'
import { getCaseAccent, getCasePriorityLabel, getCaseStatusLabel, getReadableCaseHint } from '../utils/flow'

const STATUSES = [
  { key: '',          label: 'Все' },
  { key: 'open',      label: 'Активные' },
  { key: 'watching',  label: 'Наблюдение' },
  { key: 'resolved',  label: 'Решённые' },
]

function timeAgo(iso?: string) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч`
  return `${Math.floor(hrs / 24)} д`
}

function CaseCard({ flowCase }: { flowCase: FlowCase }) {
  const accent = getCaseAccent(flowCase)
  const isCritical = flowCase.is_critical || flowCase.priority === 'critical'

  return (
    <Link to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div className="glass-card" style={{
        padding: '14px 14px 12px',
        borderLeft: `3px solid ${accent}`,
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10, marginBottom: 5 }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.3, flex: 1 }}>
            {isCritical && <span style={{ marginRight: 5 }}>🔴</span>}
            {flowCase.title}
          </div>
          {/* Signal count badge */}
          <span className="chip" style={{
            background: isCritical ? 'var(--danger-bg)' : 'var(--brand-light)',
            color: isCritical ? 'var(--danger)' : 'var(--brand)',
            flexShrink: 0,
            fontWeight: 800,
            fontSize: 13,
          }}>
            {flowCase.signal_count}
          </span>
        </div>

        {/* Hint */}
        <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 9 }}>
          {getReadableCaseHint(flowCase)}
        </div>

        {/* Meta chips */}
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Status */}
          <span className="chip" style={{
            background: flowCase.status === 'open' ? '#e0e7ff'
              : flowCase.status === 'watching' ? '#e0f2fe'
              : flowCase.status === 'resolved' ? '#dcfce7'
              : 'var(--priority-low-bg)',
            color: flowCase.status === 'open' ? '#3730a3'
              : flowCase.status === 'watching' ? '#075985'
              : flowCase.status === 'resolved' ? '#15803d'
              : 'var(--text-soft)',
          }}>
            <span style={{
              width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
              background: flowCase.status === 'open' ? '#6366f1'
                : flowCase.status === 'watching' ? '#0284c7'
                : flowCase.status === 'resolved' ? '#22c55e'
                : '#94a3b8',
            }} />
            {getCaseStatusLabel(flowCase.status)}
          </span>

          {/* Priority */}
          <span className="chip" style={{
            background: isCritical ? 'var(--priority-critical-bg)' : 'var(--priority-low-bg)',
            color: isCritical ? 'var(--priority-critical-color)' : 'var(--text-soft)',
          }}>
            {getCasePriorityLabel(flowCase.priority)}
          </span>

          {flowCase.department_name && (
            <span className="chip pill-purple">{flowCase.department_name}</span>
          )}

          {/* Last update or signal count text */}
          {(flowCase as any).last_signal_at && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {timeAgo((flowCase as any).last_signal_at)}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}

export default function Cases() {
  const [items, setItems]           = useState<FlowCase[]>([])
  const [loading, setLoading]       = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') ?? ''

  useEffect(() => {
    setLoading(true)
    getCases({ page: 1, page_size: 30, ...(status ? { status } : {}) })
      .then((data) => {
        // Skip empty cases — they carry no signals yet and clutter the list.
        const filtered = (data.items ?? []).filter((c) => c.signal_count > 0)
        setItems(filtered)
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [status])

  const setFilter = (nextStatus: string) => {
    haptic.select()
    const params = new URLSearchParams(searchParams)
    if (nextStatus) params.set('status', nextStatus)
    else params.delete('status')
    setSearchParams(params)
  }

  const criticalCount = items.filter((c) => c.is_critical || c.priority === 'critical').length

  return (
    <div className="app-shell">
      {/* ── Sticky header ── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 20,
        background: 'rgba(245,247,251,0.96)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--line)',
        padding: '12px 12px 10px',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 6 }}>
          <span className="section-title">Ситуации</span>
          {!loading && items.length > 0 && (
            <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
              {criticalCount > 0 && (
                <span className="chip pill-danger">{criticalCount} крит.</span>
              )}
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {items.length} всего
              </span>
            </div>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 8 }}>
          Система собирает повторяющиеся сообщения в единую ситуацию
        </div>
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto' }} className="scrollbar-hide">
          {STATUSES.map((item) => (
            <button key={item.key} onClick={() => setFilter(item.key)}
              className={`filter-chip ${status === item.key ? 'active' : ''}`}>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ── */}
      {loading ? (
        <div style={{ padding: '48px 0' }}><Loader /></div>
      ) : items.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card">
            <div className="empty-state">
              <div className="empty-state-icon">
                {status === 'resolved' ? '✅' : status === 'watching' ? '👁' : '🗂️'}
              </div>
              <div className="empty-state-title">
                {status === 'resolved' ? 'Решённых ситуаций нет'
                  : status === 'watching' ? 'Нет ситуаций под наблюдением'
                  : status === 'open' ? 'Активных ситуаций нет'
                  : 'Ситуаций пока нет'}
              </div>
              <div className="empty-state-hint">
                {status
                  ? 'Попробуйте другой фильтр или посмотрите все ситуации.'
                  : 'Ситуации создаются автоматически, когда AI замечает похожие сообщения.'}
              </div>
              {status && (
                <button onClick={() => setFilter('')} style={{
                  marginTop: 8, padding: '8px 18px', borderRadius: 999,
                  border: 'none', cursor: 'pointer',
                  background: 'var(--brand)', color: '#fff',
                  fontSize: 13, fontWeight: 700,
                }}>
                  Показать все
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="screen-section animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map((flowCase) => (
            <CaseCard key={flowCase.id} flowCase={flowCase} />
          ))}
        </div>
      )}
    </div>
  )
}
