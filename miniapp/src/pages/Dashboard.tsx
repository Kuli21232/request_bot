import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyStats, getDigestOverview, getSignals, getCases } from '../api/client'
import type { Stats, FlowSignal, FlowCase } from '../api/client'
import { Loader } from '../components/Loader'
import WebApp from '../telegram'

const ROLE_LABEL: Record<string, string> = {
  user: 'Пользователь',
  agent: 'Агент',
  supervisor: 'Супервизор',
  admin: 'Администратор',
}

function StatCard({ value, label, color, link }: { value: number; label: string; color: string; link?: string }) {
  const inner = (
    <div
      style={{
        background: color,
        borderRadius: 16,
        padding: '16px 14px',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: `0 4px 14px ${color}55`,
      }}
    >
      <div style={{ position: 'absolute', top: -14, right: -14, width: 70, height: 70, borderRadius: '50%', background: 'rgba(255,255,255,0.12)' }} />
      <div style={{ fontSize: 32, fontWeight: 800, lineHeight: 1.1, position: 'relative' }}>{value}</div>
      <div style={{ fontSize: 12, marginTop: 4, opacity: 0.85, fontWeight: 500, position: 'relative' }}>{label}</div>
    </div>
  )

  if (link) return <Link to={link} style={{ textDecoration: 'none' }}>{inner}</Link>
  return inner
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

function ActionRow({ to, icon, label, badge }: { to: string; icon: string; label: string; badge?: number }) {
  return (
    <Link
      to={to}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '13px 16px',
        gap: 12,
        textDecoration: 'none',
        color: 'inherit',
        borderBottom: '1px solid rgba(0,0,0,0.05)',
      }}
    >
      <span style={{ fontSize: 20, width: 28, textAlign: 'center' }}>{icon}</span>
      <span style={{ fontSize: 14, flex: 1 }}>{label}</span>
      {badge != null && badge > 0 && (
        <span style={{ background: '#ef4444', color: '#fff', fontSize: 11, fontWeight: 700, borderRadius: 100, padding: '1px 7px', minWidth: 20, textAlign: 'center' }}>
          {badge}
        </span>
      )}
      <span style={{ color: '#ccc', fontSize: 18 }}>›</span>
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
    { label: 'Сигналы', value: digest?.total_signals ?? 0, color: '#2563eb', link: '/signals' },
    { label: 'Внимание', value: digest?.requires_attention ?? 0, color: '#dc2626', link: '/signals?attention=true' },
    { label: 'Кейсы', value: digest?.critical_cases ?? 0, color: '#0f766e', link: '/cases' },
    { label: 'Медиа', value: digest?.with_media ?? 0, color: '#0891b2', link: '/signals?kind=photo_report' },
  ]

  return (
    <div style={{ paddingBottom: 80 }}>
      <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 60%, #0f766e 100%)', padding: '28px 16px 40px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: -30, right: -30, width: 130, height: 130, borderRadius: '50%', background: 'rgba(255,255,255,0.07)' }} />
        <div style={{ position: 'absolute', bottom: -20, left: -20, width: 90, height: 90, borderRadius: '50%', background: 'rgba(255,255,255,0.05)' }} />
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)', marginBottom: 2 }}>Здравствуйте,</div>
        <div style={{ fontSize: 24, fontWeight: 700, color: '#fff', marginBottom: 10 }}>
          {user?.first_name ?? 'Команда'} 
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.18)', borderRadius: 100, padding: '4px 12px' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#4ade80' }} />
          <span style={{ fontSize: 12, color: '#fff', fontWeight: 500 }}>{ROLE_LABEL[stats?.role ?? 'user'] ?? stats?.role}</span>
        </div>
      </div>

      <div style={{ padding: '0 12px', marginTop: -22 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {cards.map((card) => <StatCard key={card.label} value={card.value} label={card.label} color={card.color} link={card.link} />)}
        </div>
      </div>

      {signals.length > 0 && (
        <div style={{ margin: '16px 12px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Важные сигналы</span>
            <Link to="/signals?attention=true" style={{ fontSize: 12, color: '#2481cc', textDecoration: 'none' }}>Все →</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {signals.map((signal) => (
              <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none' }}>
                <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 14, padding: '12px 14px', borderLeft: `4px solid ${signal.importance === 'critical' ? '#ef4444' : '#2481cc'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#999' }}>{signal.kind}</span>
                    <span style={{ fontSize: 11, color: '#999' }}>{timeAgo(signal.happened_at)}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {signal.summary || signal.body}
                  </div>
                  <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                    {[signal.store, signal.case_title].filter(Boolean).join(' · ')}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {cases.length > 0 && (
        <div style={{ margin: '16px 12px 0', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: '14px 14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Живые кейсы</span>
            <Link to="/cases" style={{ fontSize: 12, color: '#2481cc', textDecoration: 'none' }}>Открыть →</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {cases.map((flowCase) => (
              <Link key={flowCase.id} to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div style={{ background: '#fff', borderRadius: 12, padding: '12px 13px' }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{flowCase.title}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{flowCase.signal_count} сигналов · {timeAgo(flowCase.last_signal_at)}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div style={{ margin: '16px 12px 0', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          Быстрые действия
        </div>
        <ActionRow to="/signals" icon="🤖" label="Лента сигналов" badge={digest?.total_signals} />
        <ActionRow to="/cases" icon="🗂️" label="AI-кейсы" badge={digest?.critical_cases} />
        {isAgent && <ActionRow to="/requests" icon="📋" label="Теневые заявки" badge={stats?.new} />}
        <ActionRow to="/my" icon="👤" label="Мои заявки" />
      </div>
    </div>
  )
}
