import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getSignals, type FlowSignal } from '../api/client'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'

const FILTERS = [
  { key: '', label: 'Все' },
  { key: 'problem', label: 'Проблемы' },
  { key: 'photo_report', label: 'Фото/Видео' },
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

function badgeColor(signal: FlowSignal) {
  if (signal.is_noise) return '#64748b'
  if (signal.importance === 'critical') return '#dc2626'
  if (signal.importance === 'high') return '#ea580c'
  if (signal.has_media) return '#0f766e'
  return '#2563eb'
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
    <div style={{ paddingBottom: 80 }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--tg-theme-bg-color, #fff)', padding: '12px 12px 8px', boxShadow: '0 1px 8px rgba(0,0,0,0.06)' }}>
        <div style={{ fontSize: 19, fontWeight: 700, marginBottom: 6 }}>Поток сигналов</div>
        <div style={{ fontSize: 12, color: 'var(--tg-theme-hint-color, #999)', marginBottom: 10 }}>
          AI сортирует сообщения, медиа и повторы в живой поток
        </div>
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 8 }} className="scrollbar-hide">
          {FILTERS.map((filter) => (
            <button
              key={filter.key}
              onClick={() => setFilter(filter.key)}
              style={{
                flexShrink: 0,
                padding: '6px 12px',
                borderRadius: 100,
                border: 'none',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: 600,
                background: kind === filter.key ? '#2563eb' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
                color: kind === filter.key ? '#fff' : 'var(--tg-theme-text-color, #555)',
              }}
            >
              {filter.label}
            </button>
          ))}
          <button
            onClick={toggleAttention}
            style={{
              flexShrink: 0,
              padding: '6px 12px',
              borderRadius: 100,
              border: 'none',
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 600,
              background: requiresAttention ? '#dc2626' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
              color: requiresAttention ? '#fff' : 'var(--tg-theme-text-color, #555)',
            }}
          >
            Критичное
          </button>
        </div>
        {!loading && (
          <div style={{ fontSize: 12, color: '#94a3b8' }}>
            {items.length} из {total} сигналов
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '64px 20px', color: '#94a3b8' }}>
          <div style={{ fontSize: 42, marginBottom: 10 }}>📭</div>
          Сигналов по этому фильтру пока нет
        </div>
      ) : (
        <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((signal) => (
            <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: '13px 14px', borderLeft: `4px solid ${badgeColor(signal)}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>{signal.kind}</span>
                  {signal.case_title && (
                    <span style={{ fontSize: 11, color: '#0f766e', background: '#dcfce7', borderRadius: 100, padding: '2px 8px' }}>
                      Кейс: {signal.case_title}
                    </span>
                  )}
                  {signal.has_media && (
                    <span style={{ fontSize: 11, color: '#155e75', background: '#cffafe', borderRadius: 100, padding: '2px 8px' }}>
                      Медиа
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: '#94a3b8' }}>{timeAgo(signal.happened_at)}</span>
                </div>
                <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
                  {signal.summary || signal.body}
                </div>
                <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {signal.body}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                  {signal.store && <span style={{ fontSize: 11, color: '#475569', background: '#e2e8f0', borderRadius: 100, padding: '2px 8px' }}>{signal.store}</span>}
                  {signal.department_name && <span style={{ fontSize: 11, color: '#7c3aed', background: '#ede9fe', borderRadius: 100, padding: '2px 8px' }}>{signal.department_name}</span>}
                  {signal.recommended_action && <span style={{ fontSize: 11, color: '#9a3412', background: '#ffedd5', borderRadius: 100, padding: '2px 8px' }}>{signal.recommended_action}</span>}
                </div>
              </div>
            </Link>
          ))}

          {items.length < total && (
            <button
              onClick={loadMore}
              disabled={loadingMore}
              style={{ width: '100%', padding: '12px', borderRadius: 12, border: 'none', background: 'var(--tg-theme-secondary-bg-color, #f0f0f0)', color: '#2563eb', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
            >
              {loadingMore ? 'Загрузка...' : `Показать ещё (${total - items.length})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
