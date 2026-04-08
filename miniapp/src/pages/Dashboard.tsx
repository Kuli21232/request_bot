import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyStats, getOverview, getVolume, getRequests } from '../api/client'
import type { Stats, VolumePoint, Request } from '../api/client'
import { MiniBarChart } from '../components/MiniBarChart'
import { StatusBadge, STATUS_DOT_COLOR } from '../components/StatusBadge'
import { Loader } from '../components/Loader'
import WebApp from '../telegram'

const ROLE_LABEL: Record<string, string> = {
  user: 'Пользователь', agent: 'Агент', supervisor: 'Супервизор', admin: 'Администратор',
}

function StatCard({ value, label, color, link }: {
  value: number; label: string; color: string; link?: string
}) {
  const inner = (
    <div style={{
      background: color, borderRadius: 16, padding: '16px 14px',
      color: '#fff', position: 'relative', overflow: 'hidden',
      boxShadow: `0 4px 14px ${color}55`,
    }}>
      <div style={{ position: 'absolute', top: -14, right: -14, width: 70, height: 70, borderRadius: '50%', background: 'rgba(255,255,255,0.12)' }} />
      <div style={{ fontSize: 32, fontWeight: 800, lineHeight: 1.1, position: 'relative' }}>{value}</div>
      <div style={{ fontSize: 12, marginTop: 4, opacity: 0.85, fontWeight: 500, position: 'relative' }}>{label}</div>
    </div>
  )
  if (link) return <Link to={link} style={{ textDecoration: 'none' }}>{inner}</Link>
  return inner
}

function timeAgo(iso: string) {
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
    <Link to={to} style={{
      display: 'flex', alignItems: 'center', padding: '13px 16px', gap: 12,
      textDecoration: 'none', color: 'inherit', borderBottom: '1px solid rgba(0,0,0,0.05)',
    }}>
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
  const [volume, setVolume] = useState<VolumePoint[]>([])
  const [recent, setRecent] = useState<Request[]>([])
  const [loading, setLoading] = useState(true)
  const user = WebApp.initDataUnsafe?.user

  useEffect(() => {
    const load = async () => {
      try {
        const myStats = await getMyStats()
        const isAgent = ['agent', 'supervisor', 'admin'].includes(myStats.role)
        if (isAgent) {
          const [vol, overview, reqs] = await Promise.allSettled([
            getVolume(7), getOverview(), getRequests({ page_size: 5, status: 'new' }),
          ])
          setStats({ ...myStats, ...(overview.status === 'fulfilled' ? overview.value : {}) })
          if (vol.status === 'fulfilled') setVolume(vol.value)
          if (reqs.status === 'fulfilled') setRecent(reqs.value.items ?? [])
        } else {
          const [vol, reqs] = await Promise.allSettled([
            getVolume(7), getRequests({ my: 'true', page_size: 5 }),
          ])
          setStats(myStats)
          if (vol.status === 'fulfilled') setVolume(vol.value)
          if (reqs.status === 'fulfilled') setRecent(reqs.value.items ?? [])
        }
      } catch { /* ignore */ }
      finally { setLoading(false) }
    }
    load()
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '70vh' }}>
      <Loader />
    </div>
  )

  const isAgent = stats && ['agent', 'supervisor', 'admin'].includes(stats.role)
  const greet = () => {
    const h = new Date().getHours()
    if (h < 6) return 'Доброй ночи'; if (h < 12) return 'Доброе утро'
    if (h < 18) return 'Добрый день'; return 'Добрый вечер'
  }

  const cards = isAgent ? [
    { label: 'Новые',        value: stats?.new ?? 0,          color: '#3b82f6', link: '/requests?status=new' },
    { label: 'В работе',     value: stats?.in_progress ?? 0,  color: '#f59e0b', link: '/requests?status=in_progress' },
    { label: 'Решённые',     value: stats?.resolved ?? 0,     color: '#22c55e', link: '/requests?status=resolved' },
    { label: 'Просроченные', value: stats?.sla_breached ?? 0, color: '#ef4444', link: '/requests?sla_breached=true' },
  ] : [
    { label: 'Мои заявки',   value: stats?.total ?? 0,         color: '#3b82f6', link: '/my' },
    { label: 'В работе',     value: stats?.in_progress ?? 0,   color: '#f59e0b', link: '/my' },
    { label: 'Решённые',     value: stats?.resolved ?? 0,      color: '#22c55e', link: '/my' },
    { label: 'Просроченные', value: stats?.sla_breached ?? 0,  color: '#ef4444', link: '/my' },
  ]

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Hero header */}
      <div style={{
        background: 'linear-gradient(135deg, #1a56db 0%, #2481cc 60%, #0ea5e9 100%)',
        padding: '28px 16px 40px', position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', top: -30, right: -30, width: 130, height: 130, borderRadius: '50%', background: 'rgba(255,255,255,0.07)' }} />
        <div style={{ position: 'absolute', bottom: -20, left: -20, width: 90, height: 90, borderRadius: '50%', background: 'rgba(255,255,255,0.05)' }} />
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)', marginBottom: 2 }}>{greet()},</div>
        <div style={{ fontSize: 24, fontWeight: 700, color: '#fff', marginBottom: 10 }}>
          {user?.first_name ?? 'Пользователь'} 👋
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.18)', borderRadius: 100, padding: '4px 12px' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#4ade80' }} />
          <span style={{ fontSize: 12, color: '#fff', fontWeight: 500 }}>
            {ROLE_LABEL[stats?.role ?? 'user'] ?? stats?.role}
          </span>
        </div>
      </div>

      {/* Stat cards — overlapping header */}
      <div style={{ padding: '0 12px', marginTop: -22 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {cards.map(c => <StatCard key={c.label} value={c.value} label={c.label} color={c.color} link={c.link} />)}
        </div>
      </div>

      {/* Volume chart */}
      {volume.length > 0 && (
        <div style={{ margin: '14px 12px 0', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>📈 Активность, 7 дней</span>
            <span style={{ fontSize: 11, color: '#999' }}>{volume.reduce((s, v) => s + v.count, 0)} заявок</span>
          </div>
          <MiniBarChart data={volume} height={60} />
        </div>
      )}

      {/* Avg satisfaction for agents */}
      {isAgent && (stats as any)?.avg_satisfaction > 0 && (
        <div style={{ margin: '10px 12px 0', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ fontSize: 36 }}>⭐</div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {Number((stats as any).avg_satisfaction).toFixed(1)}<span style={{ fontSize: 14, fontWeight: 400, color: '#999' }}> / 5</span>
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>Средняя оценка решений</div>
          </div>
        </div>
      )}

      {/* Recent requests */}
      {recent.length > 0 && (
        <div style={{ margin: '16px 12px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>{isAgent ? '🆕 Новые заявки' : '📋 Последние заявки'}</span>
            <Link to={isAgent ? '/requests?status=new' : '/my'} style={{ fontSize: 12, color: '#2481cc', textDecoration: 'none' }}>Все →</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recent.map(req => (
              <Link key={req.id} to={`/requests/${req.id}`} style={{ textDecoration: 'none' }}>
                <div style={{
                  background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                  borderRadius: 14, padding: '12px 14px',
                  borderLeft: `4px solid ${STATUS_DOT_COLOR[req.status] ?? '#ddd'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#999' }}>{req.ticket_number}</span>
                    <StatusBadge status={req.status} showDot />
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {req.subject || req.body}
                  </div>
                  <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                    {timeAgo(req.created_at)}{req.department_name ? ` · ${req.department_name}` : ''}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div style={{ margin: '16px 12px 0', background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          Быстрые действия
        </div>
        {isAgent && <>
          <ActionRow to="/requests" icon="📋" label="Все заявки" badge={stats?.new} />
          <ActionRow to="/requests?assigned_to_me=true" icon="🎯" label="Назначены мне" />
          <ActionRow to="/requests?sla_breached=true" icon="⚠️" label="Просроченные SLA" badge={stats?.sla_breached} />
        </>}
        <ActionRow to="/my" icon="👤" label="Мои заявки" />
        {!isAgent && (
          <div style={{ padding: '12px 16px', fontSize: 12, color: '#999' }}>
            💡 Чтобы создать заявку — напишите сообщение в нужный топик группы
          </div>
        )}
      </div>
    </div>
  )
}
