import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCases, getDigestOverview, getMyStats, getSignals } from '../api/client'
import type { FlowCase, FlowSignal, Stats } from '../api/client'
import { Loader } from '../components/Loader'
import WebApp from '../telegram'
import {
  getCaseAccent,
  getReadableCaseHint,
  getReadableSignalTitle,
  getRecommendedActionLabel,
  getSignalAccent,
  getSignalKindLabel,
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
  if (mins < 60) return `${mins} мин назад`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч назад`
  return `${Math.floor(hrs / 24)} д назад`
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

function StepCard({ icon, title, text }: { icon: string; title: string; text: string }) {
  return (
    <div className="soft-card" style={{ padding: '14px 14px 13px' }}>
      <div style={{ fontSize: 22, marginBottom: 10 }}>{icon}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)', marginBottom: 5 }}>{title}</div>
      <div style={{ fontSize: 12, color: 'var(--text-soft)', lineHeight: 1.45 }}>{text}</div>
    </div>
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
  const [signals, setSignals] = useState<FlowSignal[]>([])
  const [cases, setCases] = useState<FlowCase[]>([])
  const [loading, setLoading] = useState(true)
  const user = WebApp.initDataUnsafe?.user

  useEffect(() => {
    const load = async () => {
      try {
        const [myStats, digestRes, signalsRes, casesRes] = await Promise.allSettled([
          getMyStats(),
          getDigestOverview(),
          getSignals({ page_size: 4, requires_attention: true }),
          getCases({ page_size: 3 }),
        ])
        if (myStats.status === 'fulfilled') setStats(myStats.value)
        if (digestRes.status === 'fulfilled') setDigest(digestRes.value)
        if (signalsRes.status === 'fulfilled') setSignals(signalsRes.value.items ?? [])
        if (casesRes.status === 'fulfilled') setCases(casesRes.value.items ?? [])
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

  const isAgent = stats && ['agent', 'supervisor', 'admin'].includes(stats.role)
  const cards = [
    { label: 'Сообщения за день', value: digest?.total_signals ?? 0, hint: 'Все сообщения, которые система разобрала по смыслу.', accent: '#1d4ed8', link: '/signals' },
    { label: 'Нужно внимание', value: digest?.requires_attention ?? 0, hint: 'То, что стоит посмотреть в первую очередь.', accent: '#dc2626', link: '/signals?attention=true' },
    { label: 'Активные ситуации', value: digest?.critical_cases ?? 0, hint: 'Повторы и связанные обсуждения собраны вместе.', accent: '#0f766e', link: '/cases' },
    { label: 'С медиа', value: digest?.with_media ?? 0, hint: 'Фото и вложения, которые уже попали в поток.', accent: '#0891b2', link: '/signals?kind=photo_report' },
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
        <div style={{ fontSize: 13, opacity: 0.76, marginBottom: 4 }}>Операционный обзор</div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8 }}>
          {user?.first_name ?? 'Команда'}
        </div>
        <div style={{ maxWidth: 320, fontSize: 14, lineHeight: 1.45, opacity: 0.92 }}>
          Система собирает сообщения из топиков, выделяет важное и объединяет похожие обсуждения в понятные ситуации.
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

      <div className="screen-section">
        <div className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 6 }}>Как это работает</div>
          <div className="section-subtitle" style={{ marginBottom: 12 }}>
            Чтобы интерфейс было проще читать, мы показываем поток в трех понятных слоях.
          </div>
          <div style={{ display: 'grid', gap: 10 }}>
            <StepCard icon="💬" title="Сообщения" text="Каждое сообщение из Telegram попадает в поток и получает краткое резюме." />
            <StepCard icon="🧩" title="Ситуации" text="Похожие сообщения система объединяет, чтобы не было дублей и шума." />
            <StepCard icon="✅" title="Задачи" text="Если нужен реальный разбор, ситуация или сообщение может уйти в работу." />
          </div>
        </div>
      </div>

      {signals.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span className="section-title" style={{ fontSize: 18 }}>Сейчас важно</span>
            <Link to="/signals?attention=true" style={{ fontSize: 12, color: '#0f766e', textDecoration: 'none', fontWeight: 700 }}>Весь поток</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {signals.map((signal) => (
              <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="glass-card" style={{ padding: '14px 15px', borderLeft: `4px solid ${getSignalAccent(signal)}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                    <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getSignalKindLabel(signal.kind)}</span>
                    {signal.has_media && <span className="pill" style={{ background: '#ecfeff', color: '#0f766e' }}>Есть медиа</span>}
                    <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-soft)' }}>{timeAgo(signal.happened_at)}</span>
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.35 }}>
                    {getReadableSignalTitle(signal)}
                  </div>
                  <div style={{ marginTop: 7, fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45 }}>
                    {[signal.store, signal.case_title, getRecommendedActionLabel(signal.recommended_action)].filter(Boolean).join(' · ') || 'Без привязки к ситуации'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {cases.length > 0 && (
        <div className="screen-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span className="section-title" style={{ fontSize: 18 }}>Живые ситуации</span>
            <Link to="/cases" style={{ fontSize: 12, color: '#0f766e', textDecoration: 'none', fontWeight: 700 }}>Открыть</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {cases.map((flowCase) => (
              <Link key={flowCase.id} to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="glass-card" style={{ padding: '15px 15px 14px', borderLeft: `4px solid ${getCaseAccent(flowCase)}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 6 }}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>{flowCase.title}</div>
                    <span className="pill" style={{ background: '#f0fdf4', color: '#0f766e' }}>{flowCase.signal_count}</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45 }}>{getReadableCaseHint(flowCase)}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="screen-section">
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 16px', fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>Быстрые переходы</div>
          <ActionRow to="/signals" icon="💬" label="Лента сообщений" hint="Весь поток с фильтрами по типу и важности." badge={digest?.total_signals} />
          <ActionRow to="/cases" icon="🧩" label="Ситуации" hint="Собранные повторы и длинные обсуждения." badge={digest?.critical_cases} />
          <ActionRow to="/topics" icon="🗂️" label="Темы Telegram" hint="Все топики группы, которые система уже видит." />
          {isAgent && <ActionRow to="/requests" icon="📋" label="Рабочие задачи" hint="То, что реально ушло исполнителю в работу." badge={stats?.new} />}
          <ActionRow to="/my" icon="👤" label="Мои задачи" hint="Назначенное лично вам и история обработки." />
        </div>
      </div>
    </div>
  )
}
