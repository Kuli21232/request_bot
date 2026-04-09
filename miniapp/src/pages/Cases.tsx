import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCases, type FlowCase } from '../api/client'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'
import { getCaseAccent, getCasePriorityLabel, getCaseStatusLabel, getReadableCaseHint } from '../utils/flow'

const STATUSES = [
  { key: '', label: 'Все' },
  { key: 'open', label: 'Активные' },
  { key: 'watching', label: 'Под наблюдением' },
  { key: 'resolved', label: 'Решенные' },
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
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Ситуации</div>
          <div className="section-subtitle" style={{ marginBottom: 12 }}>
            Здесь система собирает вместе повторяющиеся сообщения и длинные обсуждения, чтобы их можно было разобрать как одну проблему.
          </div>
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto' }} className="scrollbar-hide">
            {STATUSES.map((item) => (
              <button
                key={item.key}
                onClick={() => setFilter(item.key)}
                className={`filter-chip ${status === item.key ? 'active' : ''}`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : items.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card" style={{ textAlign: 'center', color: 'var(--text-soft)', padding: '50px 18px' }}>
            Ситуаций пока нет
          </div>
        </div>
      ) : (
        <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((flowCase) => (
            <Link key={flowCase.id} to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="glass-card" style={{ padding: '15px 15px 14px', borderLeft: `4px solid ${getCaseAccent(flowCase)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.3 }}>{flowCase.title}</div>
                  <div className="pill" style={{ background: '#ecfdf5', color: '#0f766e' }}>{flowCase.signal_count}</div>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 10 }}>
                  {getReadableCaseHint(flowCase)}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>{getCaseStatusLabel(flowCase.status)}</span>
                  <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>{getCasePriorityLabel(flowCase.priority)}</span>
                  {flowCase.department_name && <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>{flowCase.department_name}</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
