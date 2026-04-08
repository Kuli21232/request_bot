import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCase, type FlowCaseDetail } from '../api/client'
import { Loader } from '../components/Loader'

export default function CaseDetail() {
  const { id } = useParams()
  const [flowCase, setFlowCase] = useState<FlowCaseDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getCase(Number(id))
      .then(setFlowCase)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: '40px 0' }}><Loader /></div>
  if (!flowCase) return <div style={{ padding: 20, color: '#94a3b8' }}>Кейс не найден</div>

  return (
    <div style={{ padding: '14px 12px 88px' }}>
      <div style={{ background: 'linear-gradient(135deg, #0f766e 0%, #2563eb 100%)', color: '#fff', borderRadius: 18, padding: '18px 16px', marginBottom: 14 }}>
        <div style={{ fontSize: 21, fontWeight: 700 }}>{flowCase.title}</div>
        {flowCase.summary && <div style={{ marginTop: 8, fontSize: 14, opacity: 0.88 }}>{flowCase.summary}</div>}
        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.14)', borderRadius: 100, padding: '4px 10px' }}>{flowCase.status}</span>
          <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.14)', borderRadius: 100, padding: '4px 10px' }}>{flowCase.priority}</span>
          <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.14)', borderRadius: 100, padding: '4px 10px' }}>{flowCase.signal_count} сигналов</span>
        </div>
      </div>

      <section style={{ background: 'var(--tg-theme-secondary-bg-color, #f8fafc)', borderRadius: 16, padding: 14, marginBottom: 12 }}>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>AI-подсказка</div>
        <div style={{ fontSize: 14, lineHeight: 1.45, color: '#334155' }}>
          {flowCase.recommended_action || 'Пока без рекомендации, кейс просто наблюдается.'}
        </div>
      </section>

      <section style={{ background: 'var(--tg-theme-secondary-bg-color, #f8fafc)', borderRadius: 16, padding: 14 }}>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>Таймлайн сигналов</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(flowCase.signals ?? []).map((signal) => (
            <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div style={{ background: '#fff', borderRadius: 12, padding: '12px 13px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{signal.summary || signal.body}</div>
                <div style={{ fontSize: 12, color: '#64748b' }}>{signal.store || 'Без точки'} · {signal.kind}</div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
