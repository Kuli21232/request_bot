import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getSignal, type FlowSignalDetail } from '../api/client'
import { Loader } from '../components/Loader'

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (value == null || value === '') return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 12, color: '#94a3b8' }}>{label}</div>
      <div style={{ fontSize: 14, color: 'var(--tg-theme-text-color, #0f172a)' }}>{value}</div>
    </div>
  )
}

export default function SignalDetail() {
  const { id } = useParams()
  const [signal, setSignal] = useState<FlowSignalDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getSignal(Number(id))
      .then(setSignal)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div style={{ padding: '40px 0' }}><Loader /></div>
  }

  if (!signal) {
    return <div style={{ padding: 20, color: '#94a3b8' }}>Сигнал не найден</div>
  }

  return (
    <div style={{ padding: '14px 12px 88px' }}>
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%)', color: '#fff', borderRadius: 18, padding: '18px 16px', marginBottom: 14 }}>
        <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6, textTransform: 'uppercase' }}>{signal.kind}</div>
        <div style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.2 }}>{signal.summary || 'Сигнал потока'}</div>
        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {signal.store && <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.14)', borderRadius: 100, padding: '4px 10px' }}>{signal.store}</span>}
          {signal.case_title && <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.14)', borderRadius: 100, padding: '4px 10px' }}>{signal.case_title}</span>}
          {signal.recommended_action && <span style={{ fontSize: 12, background: 'rgba(255,255,255,0.14)', borderRadius: 100, padding: '4px 10px' }}>{signal.recommended_action}</span>}
        </div>
      </div>

      <div style={{ display: 'grid', gap: 12 }}>
        <section style={{ background: 'var(--tg-theme-secondary-bg-color, #f8fafc)', borderRadius: 16, padding: 14 }}>
          <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8 }}>Оригинальное сообщение</div>
          <div style={{ fontSize: 15, whiteSpace: 'pre-wrap', lineHeight: 1.45 }}>{signal.body}</div>
        </section>

        <section style={{ background: 'var(--tg-theme-secondary-bg-color, #f8fafc)', borderRadius: 16, padding: 14 }}>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>AI-разбор</div>
          <div style={{ display: 'grid', gap: 12 }}>
            <Field label="Важность" value={signal.importance} />
            <Field label="Действие" value={signal.actionability} />
            <Field label="Топик" value={signal.topic_label} />
            <Field label="Отдел" value={signal.department_name} />
            <Field label="Рекомендация" value={signal.recommended_action} />
            <Field label="Черновая заявка" value={signal.request_ticket} />
          </div>
        </section>

        {signal.case_id && (
          <Link to={`/cases/${signal.case_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
            <section style={{ background: '#ecfeff', borderRadius: 16, padding: 14, border: '1px solid #a5f3fc' }}>
              <div style={{ fontSize: 12, color: '#0f766e', marginBottom: 6 }}>Связанный кейс</div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{signal.case_title}</div>
            </section>
          </Link>
        )}
      </div>
    </div>
  )
}
