import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getSignal, type FlowSignalDetail } from '../api/client'
import { AuthorAvatar } from '../components/AuthorAvatar'
import { Loader } from '../components/Loader'
import { MediaGallery } from '../components/MediaGallery'
import {
  getImportanceLabel,
  getReadableSignalTitle,
  getRecommendedActionLabel,
  getSignalKindLabel,
} from '../utils/flow'

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (value == null || value === '') return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 12, color: 'var(--text-soft)' }}>{label}</div>
      <div style={{ fontSize: 14, color: 'var(--text-main)', lineHeight: 1.45 }}>{value}</div>
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
    return (
      <div style={{ padding: '40px 0' }}>
        <Loader />
      </div>
    )
  }

  if (!signal) {
    return <div style={{ padding: 20, color: 'var(--text-soft)' }}>Сообщение не найдено</div>
  }

  const actionLabel =
    getRecommendedActionLabel(signal.actionability) ||
    getRecommendedActionLabel(signal.recommended_action) ||
    'Пока просто наблюдать'

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div
          className="glass-card"
          style={{
            padding: '18px 16px',
            background: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 70%, #0f766e 100%)',
            color: '#fff',
          }}
        >
          <div className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff', marginBottom: 10 }}>
            {getSignalKindLabel(signal.kind)}
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1.2 }}>{getReadableSignalTitle(signal)}</div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {signal.store && (
              <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
                {signal.store}
              </span>
            )}
            {signal.case_title && (
              <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
                {signal.case_title}
              </span>
            )}
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
              {actionLabel}
            </span>
          </div>
        </div>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 8 }}>Что написал человек</div>
          <div style={{ fontSize: 15, whiteSpace: 'pre-wrap', lineHeight: 1.55, color: 'var(--text-main)' }}>
            {signal.body}
          </div>
        </section>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 10 }}>Как система это поняла</div>
          <div style={{ display: 'grid', gap: 14 }}>
            <Field label="Тип сообщения" value={getSignalKindLabel(signal.kind)} />
            <Field label="Оценка важности" value={getImportanceLabel(signal.importance)} />
            <Field label="Что делать дальше" value={actionLabel} />
            <Field label="Тема Telegram" value={signal.topic_label} />
            <Field label="Отдел" value={signal.department_name} />
            <Field label="Рабочая задача" value={signal.request_ticket} />
          </div>
        </section>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 10 }}>Кто участвует</div>
          <div style={{ display: 'grid', gap: 14 }}>
            {signal.submitter_id ? (
              <Link to={`/team/${signal.submitter_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="soft-card" style={{ padding: '13px 13px 12px', display: 'flex', gap: 12, alignItems: 'center' }}>
                  <AuthorAvatar name={signal.submitter_name} userId={signal.submitter_id} size={40} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 3 }}>Отправитель</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>
                      {signal.submitter_name || 'Сотрудник'}
                    </div>
                    {signal.submitter_username && (
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>@{signal.submitter_username}</div>
                    )}
                  </div>
                </div>
              </Link>
            ) : (
              <Field label="Отправитель" value="Не определён" />
            )}
            {signal.responsible_user_id ? (
              <Link to={`/team/${signal.responsible_user_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="soft-card" style={{ padding: '13px 13px 12px' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 6 }}>Ответственный за ситуацию</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>
                    {signal.responsible_user_name}
                  </div>
                </div>
              </Link>
            ) : (
              <Field label="Ответственный за ситуацию" value="Пока не назначен" />
            )}
            {signal.suggested_owner_name && <Field label="Кого рекомендует AI" value={signal.suggested_owner_name} />}
          </div>
        </section>
      </div>

      {signal.media && signal.media.length > 0 && (
        <div className="screen-section">
          <MediaGallery items={signal.media} title="Вложения" compact />
        </div>
      )}

      {signal.case_id && (
        <div className="screen-section">
          <Link to={`/cases/${signal.case_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
            <section
              className="glass-card"
              style={{
                padding: 16,
                border: '1px solid rgba(15,118,110,0.18)',
                background: 'linear-gradient(180deg, rgba(236,253,245,0.92), rgba(255,255,255,0.94))',
              }}
            >
              <div style={{ fontSize: 12, color: '#0f766e', marginBottom: 6, fontWeight: 700 }}>
                Сообщение уже привязано
              </div>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-main)' }}>{signal.case_title}</div>
              <div style={{ fontSize: 13, color: 'var(--text-soft)', marginTop: 6 }}>
                Открыть общую ситуацию и посмотреть похожие сообщения.
              </div>
            </section>
          </Link>
        </div>
      )}
    </div>
  )
}
