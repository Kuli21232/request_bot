import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getTopicSections, type TopicSection } from '../api/client'
import { AuthorAvatar } from '../components/AuthorAvatar'
import { Loader } from '../components/Loader'
import { haptic } from '../telegram'
import {
  getCasePriorityLabel,
  getReadableSignalTitle,
  getRecommendedActionLabel,
  getSectionAccent,
  getSignalKindHint,
  getSignalKindLabel,
  getTopicKindLabel,
  getTopicSectionSummary,
  isGenericTopicTitle,
} from '../utils/flow'

const FILTERS = [
  { key: '',             label: 'Все' },
  { key: 'problem',     label: 'Проблемы' },
  { key: 'photo_report',label: 'Фото' },
  { key: 'delivery',    label: 'Доставка' },
  { key: 'finance',     label: 'Финансы' },
  { key: 'compliance',  label: 'ЕГАИС' },
]

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

/* ─── Signal row inside a topic section ─────────────────────── */
function SignalRow({ signal }: { signal: any }) {
  const accent = signal.importance === 'critical' ? 'var(--danger)'
    : signal.importance === 'high' ? 'var(--warning)'
    : 'transparent'
  return (
    <Link to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: 10,
        padding: '11px 0 11px 10px',
        borderBottom: '1px solid var(--line)',
        borderLeft: accent === 'transparent' ? 'none' : `3px solid ${accent}`,
        marginLeft: accent === 'transparent' ? 0 : -10,
        paddingLeft: accent === 'transparent' ? 0 : 7,
      }}>
        <AuthorAvatar name={signal.submitter_name} userId={signal.submitter_id} size={26} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'baseline', marginBottom: 2 }}>
            <span style={{
              fontSize: 12, fontWeight: 700, color: 'var(--text-main)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 140,
            }}>
              {signal.submitter_name || 'Автор не определён'}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto', flexShrink: 0 }}>
              {timeAgo(signal.happened_at)}
            </span>
          </div>
          <div style={{
            fontSize: 13, fontWeight: 500, color: 'var(--text-main)',
            lineHeight: 1.4,
            overflow: 'hidden', display: '-webkit-box',
            WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
          }}>
            {getReadableSignalTitle(signal)}
          </div>
          <div style={{ display: 'flex', gap: 5, marginTop: 5, flexWrap: 'wrap', alignItems: 'center' }}>
            <span className="chip" style={{ background: '#eff6ff', color: '#1e40af' }} title={getSignalKindHint(signal.kind)}>
              {getSignalKindLabel(signal.kind)}
            </span>
            {signal.store && (
              <span className="chip pill-neutral">{signal.store}</span>
            )}
            {signal.requires_attention && (
              <span className="chip" style={{ background: '#fee2e2', color: '#b91c1c' }}>⚠ Внимание</span>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}

/* ─── Case row inside a topic section ───────────────────────── */
function CaseRow({ flowCase }: { flowCase: any }) {
  return (
    <Link to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 0',
        borderBottom: '1px solid var(--line)',
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8, flexShrink: 0,
          background: flowCase.is_critical ? 'var(--danger-bg)' : 'var(--brand-light)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13,
        }}>
          {flowCase.is_critical ? '🔴' : '📂'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 13, fontWeight: 600, color: 'var(--text-main)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {flowCase.title}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-soft)', marginTop: 1 }}>
            {flowCase.signal_count} сообщений · {getCasePriorityLabel(flowCase.priority)}
          </div>
        </div>
        <span style={{ fontSize: 16, color: 'var(--text-muted)' }}>›</span>
      </div>
    </Link>
  )
}

/* ─── Topic section card ─────────────────────────────────────── */
function SectionCard({ section }: { section: TopicSection }) {
  const accent = getSectionAccent(section)
  const hasAttention = section.stats.attention_count > 0
  const hasCases     = section.cases.length > 0
  const hasSignals   = section.signals.length > 0

  return (
    <div className="glass-card" style={{ padding: '14px 14px 12px', borderLeft: `3px solid ${accent}` }}>
      {/* ── Topic header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
        <span style={{ fontSize: 22, lineHeight: 1, flexShrink: 0 }}>{section.icon_emoji || '🧵'}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 3 }}>
            <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>
              {isGenericTopicTitle(section.topic_title)
                ? `${getTopicKindLabel(section.topic_kind)}${section.group_title ? ` · ${section.group_title}` : ''}`
                : section.topic_title}
            </span>
            {!isGenericTopicTitle(section.topic_title) && (
              <span className="chip" style={{ background: '#eff6ff', color: '#1e40af' }} title="Роль топика в общем потоке">
                {getTopicKindLabel(section.topic_kind)}
              </span>
            )}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.4 }}>
            {section.group_title && <span style={{ color: 'var(--brand)', fontWeight: 600 }}>{section.group_title} · </span>}
            {getTopicSectionSummary(section)}
          </div>
        </div>
      </div>

      {/* ── Metrics strip ── */}
      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
        <span className="chip pill-neutral">
          {section.stats.signal_count} сигн.
        </span>
        {hasAttention && (
          <span className="chip pill-warn">⚠ {section.stats.attention_count} внимание</span>
        )}
        {section.stats.media_count > 0 && (
          <span className="chip pill-brand">📷 {section.stats.media_count}</span>
        )}
        {section.stats.open_case_count > 0 && (
          <span className="chip pill-purple">🗂 {section.stats.open_case_count} ситуации</span>
        )}
        {section.automation?.recommended_action && (
          <span className="chip pill-neutral" style={{ marginLeft: 'auto' }}>
            {getRecommendedActionLabel(section.automation.recommended_action)}
          </span>
        )}
        {section.automation?.last_signal_at && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center' }}>
            {timeAgo(section.automation.last_signal_at)}
          </span>
        )}
      </div>

      {/* ── Cases ── */}
      {hasCases && (
        <div style={{ marginBottom: 6 }}>
          <div className="label-xs" style={{ marginBottom: 4 }}>Ситуации</div>
          {section.cases.map((c) => <CaseRow key={c.id} flowCase={c} />)}
        </div>
      )}

      {/* ── Recent signals ── */}
      {hasSignals && (
        <div>
          <div className="label-xs" style={{ marginTop: hasCases ? 10 : 0, marginBottom: 4 }}>
            Последние сообщения
          </div>
          {section.signals.map((s, i) => (
            <div key={s.id} style={i === section.signals.length - 1 ? { borderBottom: 'none' } : {}}>
              <SignalRow signal={s} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Page ───────────────────────────────────────────────────── */
export default function Signals() {
  const [sections, setSections]     = useState<TopicSection[]>([])
  const [loading, setLoading]       = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const kind             = searchParams.get('kind') ?? ''
  const requiresAttention = searchParams.get('attention') === 'true'

  const loadSections = () => {
    setLoading(true)
    setFetchError(null)
    getTopicSections({
      limit_topics: 16,
      signals_per_topic: 4,
      cases_per_topic: 3,
      ...(kind ? { kind } : {}),
      ...(requiresAttention ? { requires_attention: true } : {}),
    })
      .then((data) => setSections(data.items ?? []))
      .catch((err) => {
        const status = err?.response?.status
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Неизвестная ошибка'
        setFetchError(status ? `${status}: ${detail}` : detail)
        setSections([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadSections()
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
      {/* ── Sticky header ── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 20,
        background: 'rgba(245,247,251,0.96)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--line)',
        padding: '12px 12px 10px',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
          <span className="section-title">Поток по топикам</span>
          {!loading && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>
              {sections.length} разд.
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto' }} className="scrollbar-hide">
          {FILTERS.map((f) => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`filter-chip ${kind === f.key ? 'active' : ''}`}>
              {f.label}
            </button>
          ))}
          <button
            onClick={toggleAttention}
            className={`filter-chip ${requiresAttention ? 'active' : ''}`}
            style={requiresAttention ? { background: 'linear-gradient(135deg, #dc2626, #ea580c)' } : undefined}
          >
            ⚠ Внимание
          </button>
        </div>
      </div>

      {/* ── Content ── */}
      {loading ? (
        <div style={{ padding: '48px 0' }}><Loader /></div>
      ) : fetchError ? (
        <div className="screen-section">
          <div className="glass-card">
            <div className="empty-state">
              <div className="empty-state-icon">⚠️</div>
              <div className="empty-state-title">Ошибка загрузки</div>
              <div className="empty-state-hint" style={{ fontFamily: 'monospace', fontSize: 11 }}>
                {fetchError}
              </div>
              <button
                onClick={loadSections}
                style={{
                  marginTop: 10, padding: '8px 18px', borderRadius: 999,
                  border: 'none', cursor: 'pointer',
                  background: 'var(--brand)', color: '#fff',
                  fontSize: 13, fontWeight: 700,
                }}
              >
                Повторить
              </button>
            </div>
          </div>
        </div>
      ) : sections.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card">
            <div className="empty-state">
              <div className="empty-state-icon">🗂️</div>
              <div className="empty-state-title">Разделов не найдено</div>
              <div className="empty-state-hint">
                По выбранным фильтрам нет заполненных топиков.
                Попробуйте сбросить фильтр.
              </div>
              {(kind || requiresAttention) && (
                <button
                  onClick={() => { setFilter(''); if (requiresAttention) toggleAttention() }}
                  style={{
                    marginTop: 8, padding: '8px 18px', borderRadius: 999,
                    border: 'none', cursor: 'pointer',
                    background: 'var(--brand)', color: '#fff',
                    fontSize: 13, fontWeight: 700,
                  }}
                >
                  Сбросить фильтры
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="screen-section animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sections.map((section) => (
            <SectionCard key={section.topic_id} section={section} />
          ))}
        </div>
      )}
    </div>
  )
}
