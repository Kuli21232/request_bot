import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getMyProfile, getTeamUsers, type TeamUser } from '../api/client'
import { Loader } from '../components/Loader'

function formatLastSeen(value?: string) {
  if (!value) return 'нет активности'
  const date = new Date(value)
  return (
    date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) +
    ' ' +
    date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  )
}

function roleLabel(role: string) {
  return (
    {
      admin: 'Администратор',
      supervisor: 'Координатор',
      agent: 'Исполнитель',
      user: 'Сотрудник',
    }[role] || role
  )
}

export default function Team() {
  const navigate = useNavigate()
  const [items, setItems] = useState<TeamUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [isStaffView, setIsStaffView] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const data = await getTeamUsers(search ? { search } : undefined)
        if (cancelled) return
        setItems(data)
        setIsStaffView(true)
      } catch (error: any) {
        if (error?.response?.status === 403) {
          const profile = await getMyProfile()
          if (cancelled) return
          setIsStaffView(false)
          navigate(`/team/${profile.id}`, { replace: true })
          return
        }
        if (!cancelled) setItems([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [navigate, search])

  if (!isStaffView && loading) {
    return (
      <div style={{ padding: '40px 0' }}>
        <Loader />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Команда</div>
          <div className="section-subtitle" style={{ marginBottom: 12 }}>
            Здесь видны профили сотрудников, их текущая нагрузка, ключевые темы и открытые ответственности.
          </div>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Поиск по имени, username или email"
            style={{
              width: '100%',
              borderRadius: 16,
              border: '1px solid rgba(148,163,184,0.22)',
              background: 'rgba(248,250,252,0.9)',
              padding: '12px 14px',
              fontSize: 14,
              outline: 'none',
            }}
          />
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px 0' }}>
          <Loader />
        </div>
      ) : items.length === 0 ? (
        <div className="screen-section">
          <div className="glass-card" style={{ textAlign: 'center', padding: '56px 20px', color: 'var(--text-soft)' }}>
            Профили пока не найдены
          </div>
        </div>
      ) : (
        <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((user) => (
            <Link key={user.id} to={`/team/${user.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="glass-card" style={{ padding: '14px 15px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div
                    style={{
                      width: 46,
                      height: 46,
                      borderRadius: 16,
                      background: 'linear-gradient(135deg, #dbeafe, #dcfce7)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 800,
                      color: '#0f172a',
                    }}
                  >
                    {(user.first_name || 'U').slice(0, 1).toUpperCase()}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 5 }}>
                      <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>
                        {[user.first_name, user.last_name].filter(Boolean).join(' ')}
                      </div>
                      <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>
                        {roleLabel(user.role)}
                      </span>
                      {Boolean(user.assigned_open_case_count) && (
                        <span className="pill" style={{ background: '#ecfccb', color: '#3f6212' }}>
                          Ответственность: {user.assigned_open_case_count}
                        </span>
                      )}
                      {Boolean(user.critical_case_count) && (
                        <span className="pill" style={{ background: '#fef2f2', color: '#b91c1c' }}>
                          Критичных: {user.critical_case_count}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>
                      {user.username ? `@${user.username}` : 'без username'}
                    </div>
                    {user.ai_summary && (
                      <div style={{ fontSize: 12, color: 'var(--text-main)', lineHeight: 1.5, marginTop: 8 }}>
                        {user.ai_summary}
                      </div>
                    )}
                    {user.top_topics && user.top_topics.length > 0 && (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                        {user.top_topics.slice(0, 3).map((topic) => (
                          <span key={`${user.id}-${topic.topic_title}`} className="pill" style={{ background: '#f8fafc', color: '#334155' }}>
                            {topic.topic_title}
                          </span>
                        ))}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 8 }}>
                      Активность: {formatLastSeen(user.last_active_at)} · Сообщений: {user.submitted_signal_count ?? 0}
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
