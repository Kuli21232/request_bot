import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getTopicSections, type TopicSection } from '../api/client'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'
import {
  getCasePriorityLabel,
  getReadableSignalTitle,
  getRecommendedActionLabel,
  getSectionAccent,
  getSignalKindLabel,
  getTopicKindLabel,
  getTopicSectionSummary,
} from '../utils/flow'

const FILTERS = [
  { key: '', label: 'Все' },
  { key: 'problem', label: 'Проблемы' },
  { key: 'photo_report', label: 'Фото и видео' },
  { key: 'delivery', label: 'Доставка' },
  { key: 'finance', label: 'Финансы' },
  { key: 'compliance', label: 'ЕГАИС и контроль' },
]

function timeAgo(iso?: string) {
  if (!iso) return 'без даты'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч`
  return `${Math.floor(hrs / 24)} д`
}

export default function Signals() {
  const [sections, setSections] = useState<TopicSection[]>([])
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const kind = searchParams.get('kind') ?? ''
  const requiresAttention = searchParams.get('attention') === 'true'

  useEffect(() => {
    setLoading(true)
    getTopicSections({
      limit_topics: 16,
      signals_per_topic: 4,
      cases_per_topic: 3,
      ...(kind ? { kind } : {}),
      ...(requiresAttention ? { requires_attention: true } : {}),
    })
      .then((data) => setSections(data.items ?? []))
      .catch(() => setSections([]))
      .finally(() => setLoading(false))
  }, [kind, requiresAttention])

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
          <div className="section-title" style={{ marginBottom: 4 }}>Поток по топикам</div>
          <div className="section-subtitle" style={{ marginBottom: 12 }}>
            Каждая тема теперь собрана в свой раздел: внутри видно, что происходит в топике, что AI считает важным и какие сообщения относятся именно к нему.
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
              Требует внимания
            </button>
          </div>
          {!loading && (
            <div style={{ fontSize: 12, color: 'var(--text-soft)' }}>
              Разделов: {sections.length}
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}><Loader /></div>
      ) : sections.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card" style={{ textAlign: 'center', padding: '56px 20px', color: 'var(--text-soft)' }}>
            <div style={{ fontSize: 42, marginBottom: 10 }}>🗂️</div>
            По этим условиям пока нет заполненных разделов
          </div>
        </div>
      ) : (
        <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sections.map((section) => (
            <div
              key={section.topic_id}
              className="glass-card"
              style={{ padding: '16px 15px 14px', borderLeft: `4px solid ${getSectionAccent(section)}` }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 10 }}>
                <div style={{ fontSize: 22, lineHeight: 1 }}>{section.icon_emoji || '🧵'}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 5 }}>
                    <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-main)' }}>{section.topic_title}</div>
                    <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getTopicKindLabel(section.topic_kind)}</span>
                    <span className="pill" style={{ background: '#f0fdf4', color: '#0f766e' }}>{section.group_title || 'Группа'}</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>
                    {getTopicSectionSummary(section)}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>Сигналы: {section.stats.signal_count}</span>
                <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>Внимание: {section.stats.attention_count}</span>
                <span className="pill" style={{ background: '#ecfeff', color: '#155e75' }}>Медиа: {section.stats.media_count}</span>
                <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>Ситуации: {section.stats.open_case_count}</span>
                {section.automation?.recommended_action && (
                  <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
                    {getRecommendedActionLabel(section.automation.recommended_action)}
                  </span>
                )}
                {section.automation?.last_signal_at && (
                  <span className="pill" style={{ background: '#f8fafc', color: '#475569' }}>
                    Обновлено {timeAgo(section.automation.last_signal_at)}
                  </span>
                )}
              </div>

              {section.cases.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.02em', color: '#475569', marginBottom: 8 }}>
                    Связанные ситуации
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {section.cases.map((flowCase) => (
                      <Link key={flowCase.id} to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        <div className="soft-card" style={{ padding: '12px 12px 11px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>{flowCase.title}</div>
                            <span className="pill" style={{ background: '#fef3c7', color: '#92400e' }}>
                              {getCasePriorityLabel(flowCase.priority)}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-soft)' }}>
                            Сообщений: {flowCase.signal_count}
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.02em', color: '#475569', marginBottom: 8 }}>
                  Последние сообщения
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {section.signals.map((signal) => (
                    <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                      <div className="soft-card" style={{ padding: '12px 12px 11px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                          <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getSignalKindLabel(signal.kind)}</span>
                          {signal.store && <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>{signal.store}</span>}
                          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-soft)' }}>{timeAgo(signal.happened_at)}</span>
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)', marginBottom: 5 }}>
                          {getReadableSignalTitle(signal)}
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.45 }}>
                          {signal.body}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
