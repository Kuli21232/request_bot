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
import { Loader } from '../components/Loader'
import WebApp from '../telegram'
import {
  getRecommendedActionLabel,
  getSectionAccent,
  getTopicSectionSummary,
} from '../utils/flow'

const ROLE_LABEL: Record<string, string> = {
  user: 'Сотрудник',
  agent: 'Исполнитель',
  supervisor: 'Координатор',
  admin: 'Администратор',
}

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

function StatCard({
  value,
  label,
  hint,
  accent,
  link,
}: {
  value: number
  label: string
  hint: string
  accent: string
  link: string
}) {
  return (
    <Link to={link} style={{ textDecoration: 'none' }}>
      <div
        className="glass-card"
        style={{
          padding: '16px 15px',
          minHeight: 120,
          position: 'relative',
          overflow: 'hidden',
          background: `linear-gradient(180deg, rgba(255,255,255,0.94), rgba(255,255,255,0.82)), radial-gradient(circle at top right, ${accent}1f, transparent 42%)`,
        }}
      >
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: 14,
            background: `${accent}16`,
            color: accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: 18,
            marginBottom: 12,
          }}
        >
          {value}
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.45, marginTop: 6 }}>{hint}</div>
      </div>
    </Link>
  )
}

function ActionRow({
  to,
  icon,
  label,
  hint,
  badge,
}: {
  to: string
  icon: string
  label: string
  hint: string
  badge?: number
}) {
  return (
    <Link
      to={to}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '14px 16px',
        textDecoration: 'none',
        color: 'inherit',
        borderBottom: '1px solid rgba(15,23,42,0.06)',
      }}
    >
      <span style={{ fontSize: 22, width: 28, textAlign: 'center' }}>{icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 2 }}>{hint}</div>
      </div>
      {badge != null && badge > 0 && (
        <span className="pill" style={{ background: '#ecfeff', color: '#0f766e' }}>
          {badge}
        </span>
      )}
      <span style={{ color: '#94a3b8', fontSize: 18 }}>›</span>
    </Link>
  )
}

function BoardItem({ item }: { item: ActionBoardItem }) {
  return (
    <Link to="/signals?attention=true" style={{ textDecoration: 'none', color: 'inherit' }}>
      <div className="soft-card" style={{ padding: '14px 13px 13px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)' }}>{item.topic_title}</div>
          <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>
            {item.group_title || 'Группа'}
          </span>
          <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
            {getRecommendedActionLabel(item.recommended_action)}
          </span>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 8 }}>
          {item.summary || 'По теме стоит посмотреть свежие сообщения и связанные ситуации.'}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>
            Внимание: {item.attention_count}
          </span>
          <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>
            Ситуации: {item.open_case_count}
          </span>
          {item.critical_case_count > 0 && (
            <span className="pill" style={{ background: '#fef2f2', color: '#b91c1c' }}>
              Критичных: {item.critical_case_count}
            </span>
          )}
          {item.follow_up_needed && (
            <span className="pill" style={{ background: '#ecfccb', color: '#3f6212' }}>
              Нужен follow-up
            </span>
          )}
          {item.last_signal_at && (
            <span className="pill" style={{ background: '#f8fafc', color: '#475569' }}>
              {timeAgo(item.last_signal_at)}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}

function GroupDigestCard({ digest }: { digest: GroupDigest }) {
  return (
    <div className="glass-card" style={{ padding: '15px 15px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>{digest.group_title}</div>
        <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>
          Сообщений: {digest.signal_count}
        </span>
        {digest.critical_case_count > 0 && (
          <span className="pill" style={{ background: '#fef2f2', color: '#b91c1c' }}>
            Критичных: {digest.critical_case_count}
          </span>
        )}
      </div>
      <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 10 }}>
        {digest.recommended_focus}
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>
          Внимание: {digest.attention_count}
        </span>
        <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>
          Активные ситуации: {digest.open_case_count}
        </span>
        {digest.follow_up_topics > 0 && (
          <span className="pill" style={{ background: '#ecfccb', color: '#3f6212' }}>
            Follow-up тем: {digest.follow_up_topics}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {digest.top_topics.map((topic) => (
          <Link key={topic.topic_id} to="/signals" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="soft-card" style={{ padding: '11px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-main)' }}>{topic.topic_title}</div>
                {topic.recommended_action && (
                  <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
                    {getRecommendedActionLabel(topic.recommended_action)}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.45 }}>
                {topic.summary || 'Топик включён в сводку группы.'}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [digest, setDigest] = useState<any>(null)
  const [sections, setSections] = useState<TopicSection[]>([])
  const [actionBoard, setActionBoard] = useState<ActionBoardItem[]>([])
  const [groupDigests, setGroupDigests] = useState<GroupDigest[]>([])
  const [loading, setLoading] = useState(true)
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

        if (myStats.status === 'fulfilled') setStats(myStats.value)
        if (digestRes.status === 'fulfilled') setDigest(digestRes.value)
        if (sectionsRes.status === 'fulfilled') setSections(sectionsRes.value.items ?? [])
        if (actionRes.status === 'fulfilled') setActionBoard(actionRes.value.items ?? [])
        if (groupRes.status === 'fulfilled') setGroupDigests(groupRes.value.items ?? [])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '70vh' }}>
        <Loader />
      </div>
    )
  }

  const cards = [
    {
      label: 'Сообщения за день',
      value: digest?.total_signals ?? 0,
      hint: 'Все сообщения, которые система уже разложила по темам и приоритетам.',
      accent: '#1d4ed8',
      link: '/signals',
    },
    {
      label: 'Нужно внимание',
      value: digest?.requires_attention ?? 0,
      hint: 'Темы и сообщения, которые AI поднял выше обычного потока.',
      accent: '#dc2626',
      link: '/signals?attention=true',
    },
    {
      label: 'Критичные ситуации',
      value: digest?.critical_cases ?? 0,
      hint: 'Темы, где нужен быстрый разбор и контроль.',
      accent: '#0f766e',
      link: '/cases',
    },
    {
      label: 'С медиа',
      value: digest?.with_media ?? 0,
      hint: 'Фото и видео уже привязаны к своим топикам и ситуациям.',
      accent: '#0891b2',
      link: '/signals?kind=photo_report',
    },
  ]

  return (
    <div className="app-shell">
      <div
        style={{
          padding: '24px 14px 26px',
          background: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #0f766e 100%)',
          color: '#fff',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: -24,
            right: -20,
            width: 140,
            height: 140,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.08)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: -32,
            left: -12,
            width: 100,
            height: 100,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.06)',
          }}
        />
        <div style={{ fontSize: 13, opacity: 0.76, marginBottom: 4 }}>AI-обзор по топикам и группам</div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8 }}>
          {user?.first_name ?? 'Команда'}
        </div>
        <div style={{ maxWidth: 320, fontSize: 14, lineHeight: 1.45, opacity: 0.92 }}>
          Теперь поток собран по разделам-топикам: AI показывает, где нужен срочный разбор, где пора сделать
          follow-up, а где достаточно наблюдения и дайджеста.
        </div>
        <div
          style={{
            marginTop: 14,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 12px',
            borderRadius: 999,
            background: 'rgba(255,255,255,0.14)',
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ade80' }} />
          <span style={{ fontSize: 12, fontWeight: 700 }}>{ROLE_LABEL[stats?.role ?? 'user'] ?? 'Сотрудник'}</span>
        </div>
      </div>

      <div className="screen-section" style={{ marginTop: -18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {cards.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      </div>

      {actionBoard.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span className="section-title" style={{ fontSize: 18 }}>Что сделать сейчас</span>
            <Link to="/signals?attention=true" style={{ fontSize: 12, color: '#0f766e', textDecoration: 'none', fontWeight: 700 }}>
              Открыть поток
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {actionBoard.map((item) => (
              <BoardItem key={`${item.topic_id}-${item.recommended_action}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {groupDigests.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span className="section-title" style={{ fontSize: 18 }}>Сводки по группам</span>
            <Link to="/topics" style={{ fontSize: 12, color: '#0f766e', textDecoration: 'none', fontWeight: 700 }}>
              Все топики
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {groupDigests.map((digestItem) => (
              <GroupDigestCard key={`${digestItem.group_id ?? 'group'}-${digestItem.group_title}`} digest={digestItem} />
            ))}
          </div>
        </div>
      )}

      {sections.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span className="section-title" style={{ fontSize: 18 }}>Топики под контролем</span>
            <Link to="/signals" style={{ fontSize: 12, color: '#0f766e', textDecoration: 'none', fontWeight: 700 }}>
              Открыть все
            </Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sections.map((section) => (
              <Link key={section.topic_id} to="/signals" style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="glass-card" style={{ padding: '15px 15px 14px', borderLeft: `4px solid ${getSectionAccent(section)}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 7 }}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>
                      {section.icon_emoji || '🧵'} {section.topic_title}
                    </div>
                    <span className="pill" style={{ background: '#ecfdf5', color: '#0f766e' }}>
                      {section.group_title || 'Группа'}
                    </span>
                    {section.automation?.recommended_action && (
                      <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
                        {getRecommendedActionLabel(section.automation.recommended_action)}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 8 }}>
                    {getTopicSectionSummary(section)}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>
                      Сигналы: {section.stats.signal_count}
                    </span>
                    <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>
                      Внимание: {section.stats.attention_count}
                    </span>
                    <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>
                      Ситуации: {section.stats.open_case_count}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="screen-section">
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 16px', fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>Разделы</div>
          <ActionRow
            to="/signals"
            icon="🗂️"
            label="Поток по топикам"
            hint="Все сообщения уже разложены по темам и группам."
            badge={digest?.total_signals}
          />
          <ActionRow
            to="/topics"
            icon="🧠"
            label="Профили топиков"
            hint="Как AI понимает каждую тему и что рекомендует делать."
          />
          <ActionRow
            to="/cases"
            icon="🧩"
            label="Ситуации"
            hint="Собранные повторяющиеся проблемы и длинные истории."
            badge={digest?.critical_cases}
          />
          <ActionRow
            to="/team"
            icon="👥"
            label="Команда"
            hint="Профили сотрудников, комментарии и подписки на обновления."
          />
        </div>
      </div>
    </div>
  )
}
