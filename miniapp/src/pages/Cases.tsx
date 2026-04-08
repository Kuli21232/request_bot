import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCases, type FlowCase } from '../api/client'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'

const STATUSES = [
  { key: '', label: 'Все' },
  { key: 'open', label: 'Открыты' },
  { key: 'watching', label: 'Под наблюдением' },
  { key: 'resolved', label: 'Закрыты' },
]

export default function Cases() {
  const [items, setItems] = useState<FlowCase[]>([])
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') ?? ''

  useEffect(() => {
    setLoading(true)
    getCases({ page: 1, page_size: 30, ...(status ? { status } : {}) })
      .then((data) => setItems(data.items ?? []))
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

  return (
    <div style={{ padding: '12px 12px 88px' }}>
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Кейсы</div>
        <div style={{ fontSize: 12, color: '#94a3b8' }}>Группировка повторов и длинных проблем</div>
      </div>
      <div style={{ display: 'flex', gap: 6, overflowX: 'auto', marginBottom: 14 }} className="scrollbar-hide">
        {STATUSES.map((item) => (
          <button
            key={item.key}
            onClick={() => setFilter(item.key)}
            style={{
              flexShrink: 0,
              padding: '6px 12px',
              borderRadius: 100,
              border: 'none',
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 600,
              background: status === item.key ? '#0f766e' : 'var(--tg-theme-secondary-bg-color, #f0f0f0)',
              color: status === item.key ? '#fff' : 'var(--tg-theme-text-color, #555)',
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      {loading ? (
        <Loader />
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: '50px 16px' }}>Кейсов пока нет</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((flowCase) => (
            <Link key={flowCase.id} to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: '14px 15px', borderLeft: `4px solid ${flowCase.is_critical ? '#dc2626' : '#0f766e'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{flowCase.title}</div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>{flowCase.signal_count} сигналов</div>
                </div>
                {flowCase.summary && (
                  <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8 }}>{flowCase.summary}</div>
                )}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, background: '#e2e8f0', color: '#334155', borderRadius: 100, padding: '2px 8px' }}>{flowCase.status}</span>
                  <span style={{ fontSize: 11, background: '#ede9fe', color: '#6d28d9', borderRadius: 100, padding: '2px 8px' }}>{flowCase.priority}</span>
                  {flowCase.department_name && <span style={{ fontSize: 11, background: '#f1f5f9', color: '#475569', borderRadius: 100, padding: '2px 8px' }}>{flowCase.department_name}</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
