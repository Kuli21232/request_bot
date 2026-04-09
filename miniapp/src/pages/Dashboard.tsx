import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDigestOverview, getMyStats, getTopicSections, type Stats, type TopicSection } from '../api/client'
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

function StatCard({ value, label, hint, accent, link }: { value: number; label: string; hint: string; accent: string; link: string }) {
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
        <div style={{ width: 42, height: 42, borderRadius: 14, background: `${accent}16`, color: accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 18, marginBottom: 12 }}>
          {value}
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.45, marginTop: 6 }}>{hint}</div>
      </div>
    </Link>
  )
}

function ActionRow({ to, icon, label, hint, badge }: { to: string; icon: string; label: string; hint: string; badge?: number }) {
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

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [digest, setDigest] = useState<any>(null)
  const [sections, setSections] = useState<TopicSection[]>([])
  const [loading, setLoading] = useState(true)
  const user = WebApp.initDataUnsafe?.user

  useEffect(() => {
    const load = async () => {
      try {
        const [myStats, digestRes, sectionsRes] = await Promise.allSettled([
          getMyStats(),
          getDigestOverview(),
          getTopicSections({ limit_topics: 4, signals_per_topic: 2, cases_per_topic: 2 }),
        ])
        if (myStats.status === 'fulfilled') setStats(myStats.value)
        if (digestRes.status === 'fulfilled') setDigest(digestRes.value)
        if (sectionsRes.status === 'fulfilled') setSections(sectionsRes.value.items ?? [])
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
    { label: 'Сообщения за день', value: digest?.total_signals ?? 0, hint: 'Все сообщения, которые система уже разобрала по смыслу.', accent: '#1d4ed8', link: '/signals' },
    { label: 'Нужно внимание', value: digest?.requires_attention ?? 0, hint: 'То, что AI поднял выше остальных тем.', accent: '#dc2626', link: '/signals?attention=true' },
    { label: 'Критичные ситуации', value: digest?.critical_cases ?? 0, hint: 'Темы, где нужен быстрый разбор.', accent: '#0f766e', link: '/cases' },
    { label: 'С медиа', value: digest?.with_media ?? 0, hint: 'Фото и видео, уже привязанные к своим разделам.', accent: '#0891b2', link: '/signals?kind=photo_report' },
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
        <div style={{ position: 'absolute', top: -24, right: -20, width: 140, height: 140, borderRadius: '50%', background: 'rgba(255,255,255,0.08)' }} />
        <div style={{ position: 'absolute', bottom: -32, left: -12, width: 100, height: 100, borderRadius: '50%', background: 'rgba(255,255,255,0.06)' }} />
        <div style={{ fontSize: 13, opacity: 0.76, marginBottom: 4 }}>AI-обзор по топикам</div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8 }}>
          {user?.first_name ?? 'Команда'}
        </div>
        <div style={{ maxWidth: 320, fontSize: 14, lineHeight: 1.45, opacity: 0.92 }}>
          Теперь поток собран по разделам-топикам: AI видит, что происходит в каждой теме, и подсказывает, где нужен разбор, а где достаточно наблюдения.
        </div>
        <div style={{ marginTop: 14, display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 999, background: 'rgba(255,255,255,0.14)' }}>
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

      {sections.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span className="section-title" style={{ fontSize: 18 }}>Топики под контролем</span>
            <Link to="/signals" style={{ fontSize: 12, color: '#0f766e', textDecoration: 'none', fontWeight: 700 }}>Открыть все</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sections.map((section) => (
              <Link key={section.topic_id} to="/signals" style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="glass-card" style={{ padding: '15px 15px 14px', borderLeft: `4px solid ${getSectionAccent(section)}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 7 }}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>
                      {section.icon_emoji || '🧵'} {section.topic_title}
                    </div>
                    <span className="pill" style={{ background: '#ecfdf5', color: '#0f766e' }}>{section.group_title || 'Группа'}</span>
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
                    <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>Сигналы: {section.stats.signal_count}</span>
                    <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>Внимание: {section.stats.attention_count}</span>
                    <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>Ситуации: {section.stats.open_case_count}</span>
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
          <ActionRow to="/signals" icon="🗂️" label="Поток по топикам" hint="Все сообщения разложены по темам и группам." badge={digest?.total_signals} />
          <ActionRow to="/topics" icon="🧠" label="Профили топиков" hint="Как AI понимает каждую тему и что рекомендует делать." />
          <ActionRow to="/cases" icon="🧩" label="Ситуации" hint="Собранные повторяющиеся проблемы и длинные истории." badge={digest?.critical_cases} />
          <ActionRow to="/my" icon="👤" label="Мои задачи" hint="То, что закреплено лично за вами." />
        </div>
      </div>
    </div>
  )
}
