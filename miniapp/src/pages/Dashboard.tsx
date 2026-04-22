import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getActionBoard,
  getDigestOverview,
  getGroupDigests,
  getMyStats,
  getTopicSections,
  type ActionBoardItem,
  type GroupDigest,
  type Stats,
  type TopicSection,
} from '../api/client'
import { AiText } from '../components/AiText'
import { Loader } from '../components/Loader'
import WebApp from '../telegram'
import {
  getRecommendedActionLabel,
  getSectionAccent,
  getTopicSectionSummary,
  isGenericTopicTitle,
  getTopicKindLabel,
} from '../utils/flow'

const ROLE_LABEL: Record<string, string> = {
  user:       'Сотрудник',
  agent:      'Исполнитель',
  supervisor: 'Координатор',
  admin:      'Администратор',
}

function timeAgo(iso?: string) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин назад`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч назад`
  return `${Math.floor(hrs / 24)} д назад`
}

/* ── Stat card ─────────────────────────────────────────────── */
function StatCard({
  value, label, hint, accent, link,
}: {
  value: number; label: string; hint: string; accent: string; link: string
}) {
  return (
    <Link to={link} style={{ textDecoration: 'none' }}>
      <div className="glass-card" style={{
        padding: '16px 15px 14px',
        minHeight: 110,
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Accent dot top-right */}
        <div style={{
          position: 'absolute', top: 12, right: 14,
          width: 10, height: 10, borderRadius: '50%',
          background: accent, opacity: 0.55,
        }} />
        {/* Big number */}
        <div className="stat-num" style={{ color: accent, marginBottom: 6 }}>
          {value}
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.25 }}>
          {label}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-soft)', lineHeight: 1.4, marginTop: 4 }}>
          {hint}
        </div>
      </div>
    </Link>
  )
}

/* ── Action board item ─────────────────────────────────────── */
function BoardItem({ item }: { item: ActionBoardItem }) {
  const isUrgent = item.critical_case_count > 0 || item.priority === 'critical'
  return (
    <Link to="/signals?attention=true" style={{ textDecoration: 'none', color: 'inherit' }}>
      <div className="soft-card" style={{
        padding: '13px 14px',
        borderLeft: `3px solid ${isUrgent ? 'var(--danger)' : item.priority === 'high' ? 'var(--warning)' : 'var(--brand-2)'}`,
      }}>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 5 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.3, flex: 1 }}>
            {isGenericTopicTitle(item.topic_title)
              ? (item.group_title ? `Топик · ${item.group_title}` : 'Топик без имени')
              : item.topic_title}
          </div>
          {item.last_signal_at && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }}>
              {timeAgo(item.last_signal_at)}
            </span>
          )}
        </div>

        {/* Summary */}
        {item.summary && (
          <div style={{ marginBottom: 8 }}>
            <AiText text={item.summary} compact />
          </div>
        )}

        {/* Key metrics row */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          {item.group_title && (
            <span className="chip pill-brand2">{item.group_title}</span>
          )}
          {item.critical_case_count > 0 && (
            <span className="chip pill-danger">Крит: {item.critical_case_count}</span>
          )}
          {item.attention_count > 0 && (
            <span className="chip pill-warn">Внимание: {item.attention_count}</span>
          )}
          {item.open_case_count > 0 && (
            <span className="chip pill-purple">Ситуации: {item.open_case_count}</span>
          )}
          {item.follow_up_needed && (
            <span className="chip pill-ok">Follow-up</span>
          )}
          <span className="chip pill-neutral" style={{ marginLeft: 'auto' }}>
            {getRecommendedActionLabel(item.recommended_action)}
          </span>
        </div>
      </div>
    </Link>
  )
}

/* ── Group digest card ─────────────────────────────────────── */
function GroupDigestCard({ digest }: { digest: GroupDigest }) {
  const hasCritical = digest.critical_case_count > 0
  return (
    <div className="glass-card" style={{ padding: '14px 15px', overflow: 'hidden' }}>
      {/* Group header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>
          {digest.group_title}
        </div>
        <div style={{ display: 'flex', gap: 5 }}>
          {hasCritical && (
            <span className="chip pill-danger">🔴 {digest.critical_case_count} крит.</span>
          )}
          {digest.attention_count > 0 && (
            <span className="chip pill-warn">{digest.attention_count} внимание</span>
          )}
        </div>
      </div>

      {/* Focus recommendation */}
      <div style={{ marginBottom: 10 }}>
        <AiText text={digest.recommended_focus} compact />
      </div>

      {/* Quick stats row */}
      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10 }}>
        <span className="chip pill-neutral">Сигналов: {digest.signal_count}</span>
        {digest.open_case_count > 0 && (
          <span className="chip pill-purple">Ситуаций: {digest.open_case_count}</span>
        )}
        {digest.follow_up_topics > 0 && (
          <span className="chip pill-ok">Follow-up: {digest.follow_up_topics}</span>
        )}
      </div>

      {/* Topic list — compact rows instead of nested cards */}
      <div style={{ borderTop: '1px solid var(--line)', paddingTop: 8, display: 'flex', flexDirection: 'column', gap: 0 }}>
        {digest.top_topics.map((topic, i) => (
          <Link key={topic.topic_id} to="/signals" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '9px 0',
              borderBottom: i < digest.top_topics.length - 1 ? '1px solid var(--line)' : 'none',
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                background: 'var(--brand-light)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, color: 'var(--brand)', fontWeight: 800,
              }}>
                {(topic.topic_title || '?')[0]}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: 700, color: 'var(--text-main)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {topic.topic_title}
                </div>
                {topic.summary && (
                  <div style={{
                    fontSize: 11, color: 'var(--text-soft)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {topic.summary}
                  </div>
                )}
              </div>
              {topic.recommended_action && (
                <span className="chip pill-neutral" style={{ flexShrink: 0 }}>
                  {getRecommendedActionLabel(topic.recommended_action)}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

/* ── Nav action row ────────────────────────────────────────── */
function ActionRow({ to, icon, label, hint, badge }: {
  to: string; icon: string; label: string; hint: string; badge?: number
}) {
  return (
    <Link to={to} style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '13px 16px',
      textDecoration: 'none', color: 'inherit',
      borderBottom: '1px solid var(--line)',
    }}>
      <span style={{
        width: 36, height: 36, borderRadius: 10, flexShrink: 0,
        background: 'var(--surface-muted)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18,
      }}>
        {icon}
      </span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 1 }}>{hint}</div>
      </div>
      {badge != null && badge > 0 && (
        <span className="chip pill-danger">{badge}</span>
      )}
      <span style={{ color: 'var(--text-muted)', fontSize: 20, lineHeight: 1 }}>›</span>
    </Link>
  )
}

/* ── Topic section card (compact) ──────────────────────────── */
function TopicCard({ section }: { section: TopicSection }) {
  const accent = getSectionAccent(section)
  return (
    <Link to="/signals" style={{ textDecoration: 'none', color: 'inherit' }}>
      <div className="glass-card" style={{ padding: '13px 14px', borderLeft: `3px solid ${accent}` }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 5 }}>
          <span style={{ fontSize: 20, lineHeight: 1 }}>{section.icon_emoji || '🧵'}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 14, fontWeight: 700, color: 'var(--text-main)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              marginBottom: 2,
            }}>
              {isGenericTopicTitle(section.topic_title)
                ? `${getTopicKindLabel(section.topic_kind)}${section.group_title ? ` · ${section.group_title}` : ''}`
                : section.topic_title}
            </div>
            <AiText text={getTopicSectionSummary(section)} compact />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 6 }}>
          {section.group_title && <span className="chip pill-brand">{section.group_title}</span>}
          {section.stats.attention_count > 0 && (
            <span className="chip pill-warn">Внимание: {section.stats.attention_count}</span>
          )}
          {section.stats.open_case_count > 0 && (
            <span className="chip pill-purple">Ситуации: {section.stats.open_case_count}</span>
          )}
          <span className="chip pill-neutral" style={{ marginLeft: 'auto' }}>
            {section.stats.signal_count} сигн.
          </span>
        </div>
      </div>
    </Link>
  )
}

/* ── Dashboard page ────────────────────────────────────────── */
export default function Dashboard() {
  const [stats, setStats]               = useState<Stats | null>(null)
  const [digest, setDigest]             = useState<any>(null)
  const [sections, setSections]         = useState<TopicSection[]>([])
  const [actionBoard, setActionBoard]   = useState<ActionBoardItem[]>([])
  const [groupDigests, setGroupDigests] = useState<GroupDigest[]>([])
  const [loading, setLoading]           = useState(true)
  const user = WebApp.initDataUnsafe?.user

  useEffect(() => {
    const load = async () => {
      try {
        const [myStats, digestRes, sectionsRes, actionRes, groupRes] = await Promise.allSettled([
          getMyStats(),
          getDigestOverview(),
          getTopicSections({ limit_topics: 4, signals_per_topic: 2, cases_per_topic: 2 }),
          getActionBoard({ limit: 5 }),
          getGroupDigests({ limit_groups: 3 }),
        ])
        if (myStats.status === 'fulfilled')    setStats(myStats.value)
        if (digestRes.status === 'fulfilled')  setDigest(digestRes.value)
        if (sectionsRes.status === 'fulfilled') setSections(sectionsRes.value.items ?? [])
        if (actionRes.status === 'fulfilled')  setActionBoard(actionRes.value.items ?? [])
        if (groupRes.status === 'fulfilled')   setGroupDigests(groupRes.value.items ?? [])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '70dvh' }}>
        <Loader />
      </div>
    )
  }

  const hasCritical = (digest?.critical_cases ?? 0) > 0
  const needsAttention = (digest?.requires_attention ?? 0) > 0

  const statCards = [
    {
      label: 'Сообщений за день', value: digest?.total_signals ?? 0,
      hint: 'Разложены по топикам', accent: '#1d4ed8', link: '/signals',
    },
    {
      label: 'Нужно внимание', value: digest?.requires_attention ?? 0,
      hint: 'AI поднял выше потока', accent: '#dc2626', link: '/signals?attention=true',
    },
    {
      label: 'Критичных ситуаций', value: digest?.critical_cases ?? 0,
      hint: 'Требуют быстрого разбора', accent: '#0f766e', link: '/cases',
    },
    {
      label: 'С медиа', value: digest?.with_media ?? 0,
      hint: 'Фото и видео', accent: '#0891b2', link: '/signals?kind=photo_report',
    },
  ]

  return (
    <div className="app-shell">
      {/* ── Hero ── */}
      <div style={{
        padding: '22px 16px 28px',
        background: hasCritical
          ? 'linear-gradient(135deg, #450a0a 0%, #991b1b 50%, #b45309 100%)'
          : 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #0f766e 100%)',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', top: -30, right: -16, width: 120, height: 120, borderRadius: '50%', background: 'rgba(255,255,255,0.06)' }} />
        <div style={{ position: 'absolute', bottom: -24, left: -10, width: 88, height: 88, borderRadius: '50%', background: 'rgba(255,255,255,0.05)' }} />

        <div style={{ fontSize: 12, opacity: 0.68, marginBottom: 3, letterSpacing: '0.03em', textTransform: 'uppercase' }}>
          AI-обзор операционного потока
        </div>
        <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 6 }}>
          {user?.first_name ? `Привет, ${user.first_name}` : 'Рабочий обзор'}
        </div>

        {/* Alert if critical */}
        {hasCritical && (
          <div style={{
            marginBottom: 10,
            padding: '8px 12px',
            borderRadius: 10,
            background: 'rgba(255,255,255,0.15)',
            fontSize: 13,
            fontWeight: 600,
            lineHeight: 1.4,
          }}>
            ⚠️ Есть критичные ситуации — разберите их в первую очередь
          </div>
        )}

        {/* Hint text */}
        {!hasCritical && (
          <div style={{ fontSize: 13, lineHeight: 1.45, opacity: 0.85, maxWidth: 310, marginBottom: 10 }}>
            {needsAttention
              ? `${digest.requires_attention} тем требуют внимания — посмотрите раздел «Поток».`
              : 'Поток в норме. AI мониторит топики и покажет, если что-то изменится.'}
          </div>
        )}

        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          padding: '5px 11px', borderRadius: 999,
          background: 'rgba(255,255,255,0.13)',
          fontSize: 12, fontWeight: 700,
        }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#4ade80' }} />
          {ROLE_LABEL[stats?.role ?? 'user'] ?? 'Сотрудник'}
        </span>
      </div>

      {/* ── Stat cards grid ── */}
      <div className="screen-section" style={{ marginTop: -16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {statCards.map((card) => <StatCard key={card.label} {...card} />)}
        </div>
      </div>

      {/* ── Action board ── */}
      {actionBoard.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="section-title">Что сделать сейчас</span>
            <Link to="/signals?attention=true" style={{ fontSize: 12, color: 'var(--brand)', textDecoration: 'none', fontWeight: 700 }}>
              Весь поток →
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {actionBoard.map((item) => (
              <BoardItem key={`${item.topic_id}-${item.recommended_action}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* ── Group digests ── */}
      {groupDigests.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="section-title">Сводки по группам</span>
            <Link to="/topics" style={{ fontSize: 12, color: 'var(--brand)', textDecoration: 'none', fontWeight: 700 }}>
              Все топики →
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {groupDigests.map((d) => (
              <GroupDigestCard key={`${d.group_id ?? 'g'}-${d.group_title}`} digest={d} />
            ))}
          </div>
        </div>
      )}

      {/* ── Topics under control ── */}
      {sections.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span className="section-title">Топики под контролем</span>
            <Link to="/signals" style={{ fontSize: 12, color: 'var(--brand)', textDecoration: 'none', fontWeight: 700 }}>
              Открыть все →
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sections.map((section) => <TopicCard key={section.topic_id} section={section} />)}
          </div>
        </div>
      )}

      {/* ── Quick navigation ── */}
      <div className="screen-section" style={{ marginBottom: 8 }}>
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px 10px', fontSize: 12, fontWeight: 700, color: 'var(--text-soft)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Разделы
          </div>
          <ActionRow to="/signals" icon="🗂️" label="Поток по топикам"
            hint="Все сообщения разложены по темам" badge={digest?.total_signals} />
          <ActionRow to="/topics" icon="🧠" label="Профили топиков"
            hint="Что AI думает о каждой теме" />
          <ActionRow to="/cases" icon="🧩" label="Ситуации"
            hint="Повторяющиеся проблемы и истории" badge={digest?.critical_cases} />
          <ActionRow to="/team" icon="👥" label="Команда"
            hint="Профили сотрудников и нагрузка" />
        </div>
      </div>
    </div>
  )
}
