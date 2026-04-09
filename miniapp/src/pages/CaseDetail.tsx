import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCase, type FlowCaseDetail } from '../api/client'
import { Loader } from '../components/Loader'
import { getCasePriorityLabel, getCaseStatusLabel, getReadableSignalTitle, getRecommendedActionLabel, getSignalKindLabel } from '../utils/flow'

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
  if (!flowCase) return <div style={{ padding: 20, color: 'var(--text-soft)' }}>Ситуация не найдена</div>

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div
          className="glass-card"
          style={{
            padding: '18px 16px',
            background: 'linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%)',
            color: '#fff',
          }}
        >
          <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1.25 }}>{flowCase.title}</div>
          {flowCase.summary && <div style={{ marginTop: 9, fontSize: 14, opacity: 0.9, lineHeight: 1.45 }}>{flowCase.summary}</div>}
          <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{getCaseStatusLabel(flowCase.status)}</span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{getCasePriorityLabel(flowCase.priority)}</span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{flowCase.signal_count} сообщений</span>
          </div>
        </div>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 8 }}>Что требует внимания</div>
          <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-main)' }}>
            {getRecommendedActionLabel(flowCase.recommended_action) || 'Пока ситуация собрана для наблюдения, без обязательного действия.'}
          </div>
        </section>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 10 }}>Какие сообщения вошли</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(flowCase.signals ?? []).map((signal) => (
              <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="soft-card" style={{ padding: '12px 13px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                    <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getSignalKindLabel(signal.kind)}</span>
                    {signal.store && <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>{signal.store}</span>}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.35 }}>
                    {getReadableSignalTitle(signal)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
