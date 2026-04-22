import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCases, getSignals, getTopicDetail, type FlowCase, type FlowSignal, type Topic } from '../api/client'
import { AuthorAvatar } from '../components/AuthorAvatar'
import { Loader } from '../components/Loader'
import {
  getCasePriorityLabel,
  getCaseStatusLabel,
  getReadableSignalTitle,
  getRecommendedActionLabel,
  getSignalKindHint,
  getSignalKindLabel,
  getTopicDisplayTitle,
  getTopicKindLabel,
  getTopicSummary,
} from '../utils/flow'

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

export default function TopicDetail() {
  const { id } = useParams()
  const [topic, setTopic] = useState<Topic | null>(null)
  const [signals, setSignals] = useState<FlowSignal[]>([])
  const [cases, setCases] = useState<FlowCase[]>([])
  const [loading, setLoading] = useState(true)
  const [signalsPage, setSignalsPage] = useState(1)
  const [signalsTotal, setSignalsTotal] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    if (!id) return
    setLoading(true)
    const topicId = Number(id)
    Promise.all([
      getTopicDetail(topicId),
      getSignals({ topic_id: topicId, page_size: PAGE_SIZE, page: 1 }),
      getCases({ topic_id: topicId, page_size: 20 }),
    ])
      .then(([t, s, c]) => {
        setTopic(t)
        setSignals(s.items)
        setSignalsTotal(s.total)
        setCases(c.items)
      })
      .finally(() => setLoading(false))
  }, [id])

  const loadMoreSignals = async () => {
    const next = signalsPage + 1
    const res = await getSignals({ topic_id: Number(id), page_size: PAGE_SIZE, page: next })
    setSignals((prev) => [...prev, ...res.items])
    setSignalsPage(next)
  }

  if (loading) {
    return <div style={{ padding: '40px 0' }}><Loader /></div>
  }

  if (!topic) {
    return <div style={{ padding: 20, color: 'var(--text-soft)' }}>Топик не найден</div>
  }

  const summary = getTopicSummary(topic)
  const automation = topic.profile?.automation

  return (
    <div className="app-shell">
      {/* Header */}
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div
          className="glass-card"
          style={{
            padding: '18px 16px',
            background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0f4c5c 100%)',
            color: '#fff',
          }}
        >
          <Link
            to="/topics"
            style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', textDecoration: 'none', display: 'inline-block', marginBottom: 8 }}
          >
            ← Все топики
          </Link>
          <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1.2, marginBottom: 8 }}>
            {topic.icon_emoji || '🧵'} {getTopicDisplayTitle(topic)}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
              {getTopicKindLabel(topic.topic_kind)}
            </span>
            {topic.group_title && (
              <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
                {topic.group_title}
              </span>
            )}
            {automation?.recommended_action && (
              <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
                {getRecommendedActionLabel(automation.recommended_action)}
              </span>
            )}
          </div>
          {summary && (
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 1.5 }}>
              {summary}
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="screen-section">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          <div className="glass-card" style={{ padding: '12px 10px', textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-main)' }}>{topic.signal_count}</div>
            <div style={{ fontSize: 11, color: 'var(--text-soft)', marginTop: 2 }}>Сигналов</div>
          </div>
          <div className="glass-card" style={{ padding: '12px 10px', textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-main)' }}>{cases.length}</div>
            <div style={{ fontSize: 11, color: 'var(--text-soft)', marginTop: 2 }}>Ситуаций</div>
          </div>
          <div className="glass-card" style={{ padding: '12px 10px', textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-main)' }}>{topic.media_count}</div>
            <div style={{ fontSize: 11, color: 'var(--text-soft)', marginTop: 2 }}>Медиа</div>
          </div>
        </div>
      </div>

      {/* Cases */}
      {cases.length > 0 && (
        <div className="screen-section">
          <div className="glass-card" style={{ padding: '14px 14px 13px' }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)', marginBottom: 10 }}>
              Ситуации
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {cases.map((c) => (
                <Link key={c.id} to={`/cases/${c.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="soft-card" style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.3, flex: 1 }}>
                        {c.title}
                      </div>
                      <span
                        className="pill"
                        style={{
                          background: c.is_critical ? '#fee2e2' : c.priority === 'high' ? '#fff7ed' : '#f0fdf4',
                          color: c.is_critical ? '#b91c1c' : c.priority === 'high' ? '#9a3412' : '#14532d',
                          flexShrink: 0,
                        }}
                      >
                        {getCasePriorityLabel(c.priority)}
                      </span>
                    </div>
                    {c.summary && (
                      <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.4, marginBottom: 6 }}>
                        {c.summary}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                      <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>
                        {getCaseStatusLabel(c.status)}
                      </span>
                      <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>
                        {c.signal_count} сигн.
                      </span>
                      {c.last_signal_at && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                          {timeAgo(c.last_signal_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Signals */}
      <div className="screen-section">
        <div className="glass-card" style={{ padding: '14px 14px 13px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)' }}>
              Сигналы
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-soft)' }}>{signalsTotal} всего</span>
          </div>
          {signals.length === 0 ? (
            <div style={{ fontSize: 13, color: 'var(--text-soft)', padding: '8px 0' }}>Сигналов пока нет</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {signals.map((s, i) => (
                <Link key={s.id} to={`/signals/${s.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 10,
                      padding: '12px 0',
                      borderBottom: i < signals.length - 1 ? '1px solid var(--line)' : 'none',
                      borderLeft: `3px solid ${
                        s.importance === 'critical'
                          ? 'var(--danger)'
                          : s.importance === 'high'
                            ? 'var(--warning)'
                            : 'transparent'
                      }`,
                      paddingLeft: s.importance === 'critical' || s.importance === 'high' ? 10 : 0,
                    }}
                  >
                    <AuthorAvatar name={s.submitter_name} userId={s.submitter_id} size={28} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 3 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-main)' }}>
                          {s.submitter_name || 'Автор не определён'}
                        </span>
                        {s.submitter_username && (
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>@{s.submitter_username}</span>
                        )}
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                          {timeAgo(s.happened_at)}
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 500,
                          color: 'var(--text-main)',
                          lineHeight: 1.4,
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical',
                        }}
                      >
                        {getReadableSignalTitle(s)}
                      </div>
                      <div style={{ display: 'flex', gap: 5, marginTop: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                        <span
                          className="chip"
                          style={{ background: '#eff6ff', color: '#1e40af' }}
                          title={getSignalKindHint(s.kind)}
                        >
                          {getSignalKindLabel(s.kind)}
                        </span>
                        {s.store && <span className="chip pill-neutral">{s.store}</span>}
                        {s.requires_attention && (
                          <span className="chip" style={{ background: '#fee2e2', color: '#b91c1c' }} title="ИИ пометил как требующее внимания">
                            ⚠ Внимание
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
          {signals.length < signalsTotal && (
            <button
              type="button"
              onClick={loadMoreSignals}
              style={{
                marginTop: 12,
                width: '100%',
                padding: '10px',
                borderRadius: 12,
                border: '1px solid var(--line)',
                background: 'transparent',
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text-soft)',
                cursor: 'pointer',
              }}
            >
              Показать ещё ({signalsTotal - signals.length})
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
