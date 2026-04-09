import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getSignals, type FlowSignal } from '../api/client'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'
import {
  getImportanceLabel,
  getReadableSignalTitle,
  getRecommendedActionLabel,
  getSignalAccent,
  getSignalKindLabel,
} from '../utils/flow'

const FILTERS = [
  { key: '', label: 'Все' },
  { key: 'problem', label: 'Проблемы' },
  { key: 'photo_report', label: 'Фото и видео' },
  { key: 'delivery', label: 'Доставка' },
  { key: 'finance', label: 'Финансы' },
  { key: 'chat/noise', label: 'Шум' },
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

export default function Signals() {
  const [items, setItems] = useState<FlowSignal[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const kind = searchParams.get('kind') ?? ''
  const requiresAttention = searchParams.get('attention') === 'true'

  useEffect(() => {
    setPage(1)
    setLoading(true)
    getSignals({
      page: 1,
      page_size: 20,
      ...(kind ? { kind } : {}),
      ...(requiresAttention ? { requires_attention: true } : {}),
    })
      .then((data) => {
        setItems(data.items ?? [])
        setTotal(data.total ?? 0)
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [kind, requiresAttention])

  const loadMore = async () => {
    const nextPage = page + 1
    setLoadingMore(true)
    try {
      const data = await getSignals({
        page: nextPage,
        page_size: 20,
        ...(kind ? { kind } : {}),
        ...(requiresAttention ? { requires_attention: true } : {}),
      })
      setItems((prev) => [...prev, ...(data.items ?? [])])
      setPage(nextPage)
    } finally {
      setLoadingMore(false)
    }
  }

  const setFilter = (nextKind: string) => {
    haptic.select()
    const params = new URLSearchParams(searchParams)
    if (nextKind) params.set('kind', nextKind)
    else params.delete('kind')
    setSearchParams(params)
  }

  const toggleAttention = () => {
    haptic.select()
    const params = new URLSearchParams(searchParams)
    if (requiresAttention) params.delete('attention')
    else params.set('attention', 'true')
    setSearchParams(params)
  }

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px', position: 'sticky', top: 10, zIndex: 10 }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Лента сообщений</div>
          <div className="section-subtitle" style={{ marginBottom: 12 }}>
            Здесь все входящие сообщения из топиков. Система показывает краткий смысл, важность и связь с общей ситуацией.
          </div>
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 8 }} className="scrollbar-hide">
            {FILTERS.map((filter) => (
              <button
                key={filter.key}
                onClick={() => setFilter(filter.key)}
                className={`filter-chip ${kind === filter.key ? 'active' : ''}`}
              >
                {filter.label}
              </button>
            ))}
            <button
              onClick={toggleAttention}
              className={`filter-chip ${requiresAttention ? 'active' : ''}`}
              style={requiresAttention ? { background: 'linear-gradient(135deg, #dc2626, #ea580c)' } : undefined}
            >
              Срочно
            </button>
          </div>
          {!loading && (
            <div style={{ fontSize: 12, color: 'var(--text-soft)' }}>
              Показано {items.length} из {total}
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : items.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card" style={{ textAlign: 'center', padding: '56px 20px', color: 'var(--text-soft)' }}>
            <div style={{ fontSize: 42, marginBottom: 10 }}>💬</div>
            По этому фильтру сообщений пока нет
          </div>
        </div>
      ) : (
        <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((signal) => (
            <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="glass-card" style={{ padding: '14px 15px', borderLeft: `4px solid ${getSignalAccent(signal)}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7, flexWrap: 'wrap' }}>
                  <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getSignalKindLabel(signal.kind)}</span>
                  {signal.case_title && (
                    <span className="pill" style={{ background: '#ecfdf5', color: '#0f766e' }}>
                      Ситуация: {signal.case_title}
                    </span>
                  )}
                  {signal.has_media && (
                    <span className="pill" style={{ background: '#ecfeff', color: '#155e75' }}>
                      Медиа
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-soft)' }}>{timeAgo(signal.happened_at)}</span>
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-main)', marginBottom: 6, lineHeight: 1.35 }}>
                  {getReadableSignalTitle(signal)}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-soft)', marginBottom: 9, lineHeight: 1.45, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {signal.body}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                  {signal.store && <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>{signal.store}</span>}
                  {signal.department_name && <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>{signal.department_name}</span>}
                  <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>{getImportanceLabel(signal.importance)}</span>
                  {signal.recommended_action && (
                    <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
                      {getRecommendedActionLabel(signal.recommended_action)}
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}

          {items.length < total && (
            <button
              onClick={loadMore}
              disabled={loadingMore}
              className="glass-card"
              style={{ width: '100%', padding: '13px', borderRadius: 16, border: 'none', color: '#0f766e', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
            >
              {loadingMore ? 'Загрузка...' : `Показать еще (${total - items.length})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
