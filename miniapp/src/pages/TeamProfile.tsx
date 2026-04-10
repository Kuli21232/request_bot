import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  addProfileNote,
  getUserProfile,
  type TeamProfile as TeamProfileData,
  unwatchProfile,
  watchProfile,
} from '../api/client'
import { Loader } from '../components/Loader'
import { MediaGallery } from '../components/MediaGallery'

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

function formatDate(value?: string) {
  if (!value) return 'нет данных'
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function TeamProfile() {
  const { id } = useParams()
  const [user, setUser] = useState<TeamProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [noteText, setNoteText] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await getUserProfile(Number(id))
      setUser(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const toggleWatch = async () => {
    if (!user || !user.permissions.can_view_internal_notes || user.permissions.is_self) return
    setSaving(true)
    try {
      if (user.is_watching) await unwatchProfile(user.id)
      else await watchProfile(user.id)
      await load()
    } finally {
      setSaving(false)
    }
  }

  const submitNote = async () => {
    if (!user || !noteText.trim() || !user.permissions.can_view_internal_notes) return
    setSaving(true)
    try {
      await addProfileNote(user.id, noteText.trim(), false)
      setNoteText('')
      await load()
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '40px 0' }}>
        <Loader />
      </div>
    )
  }

  if (!user) {
    return <div style={{ padding: 20, color: 'var(--text-soft)' }}>Профиль не найден</div>
  }

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div
          className="glass-card"
          style={{
            padding: '18px 16px',
            background: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 70%, #0f766e 100%)',
            color: '#fff',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 20,
                background: 'rgba(255,255,255,0.14)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
                fontWeight: 800,
              }}
            >
              {(user.first_name || 'U').slice(0, 1).toUpperCase()}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>
                {[user.first_name, user.last_name].filter(Boolean).join(' ')}
              </div>
              <div style={{ fontSize: 13, opacity: 0.84, marginTop: 4 }}>
                {user.username ? `@${user.username}` : 'без username'} · {roleLabel(user.role)}
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
              Активность: {formatDate(user.last_active_at)}
            </span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
              Подписчиков: {user.watchers_count ?? 0}
            </span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
              Открытых ситуаций: {user.assigned_cases?.length ?? 0}
            </span>
          </div>
          {user.ai_summary && (
            <div style={{ marginTop: 14, fontSize: 14, lineHeight: 1.55, opacity: 0.95 }}>
              {user.ai_summary}
            </div>
          )}
        </div>
      </div>

      {user.ai_recommendations && user.ai_recommendations.length > 0 && (
        <div className="screen-section">
          <div className="glass-card" style={{ padding: 16 }}>
            <div className="section-title" style={{ marginBottom: 10 }}>Что важно этому человеку сейчас</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {user.ai_recommendations.map((item, index) => (
                <div key={`recommendation-${index}`} className="soft-card" style={{ padding: '12px 13px' }}>
                  <div style={{ fontSize: 14, color: 'var(--text-main)', lineHeight: 1.5 }}>{item}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="screen-section">
        <div className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ marginBottom: 10 }}>Что сейчас на человеке</div>
          {user.assigned_cases && user.assigned_cases.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {user.assigned_cases.map((flowCase) => (
                <Link key={flowCase.id} to={`/cases/${flowCase.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="soft-card" style={{ padding: '13px 13px 12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                      <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)' }}>{flowCase.title}</div>
                      <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>
                        {flowCase.primary_topic_title || 'Без топика'}
                      </span>
                      <span className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>
                        {flowCase.priority}
                      </span>
                    </div>
                    {flowCase.summary && (
                      <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45 }}>{flowCase.summary}</div>
                    )}
                    <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 8 }}>
                      {flowCase.request_ticket ? `Задача ${flowCase.request_ticket} · ` : ''}
                      {flowCase.last_signal_at ? `Последний сигнал ${formatDate(flowCase.last_signal_at)}` : 'Открыто'}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-soft)' }}>Сейчас на человека не назначено открытых ситуаций.</div>
          )}
        </div>
      </div>

      <div className="screen-section">
        <div className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ marginBottom: 10 }}>Активность по топикам</div>
          {user.topic_groups && user.topic_groups.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {user.topic_groups.map((topic) => (
                <div key={`${topic.topic_id ?? 'none'}-${topic.topic_title}`} className="soft-card" style={{ padding: '14px 14px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                    <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>{topic.topic_title}</div>
                    {topic.group_title && (
                      <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>
                        {topic.group_title}
                      </span>
                    )}
                    <span className="pill" style={{ background: '#f8fafc', color: '#334155' }}>
                      Сообщений: {topic.signal_count}
                    </span>
                    {topic.request_count > 0 && (
                      <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
                        Задач: {topic.request_count}
                      </span>
                    )}
                    {topic.media_count > 0 && (
                      <span className="pill" style={{ background: '#ecfeff', color: '#0f766e' }}>
                        Медиа: {topic.media_count}
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {topic.items.slice(0, 12).map((item) => (
                      <Link key={item.id} to={`/signals/${item.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        <div
                          style={{
                            borderRadius: 16,
                            background: 'rgba(255,255,255,0.88)',
                            border: '1px solid rgba(148,163,184,0.12)',
                            padding: '11px 12px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                            {item.request_ticket && (
                              <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>
                                {item.request_ticket}
                              </span>
                            )}
                            {item.case_title && (
                              <span className="pill" style={{ background: '#f5f3ff', color: '#6d28d9' }}>
                                {item.case_title}
                              </span>
                            )}
                            {item.has_media && (
                              <span className="pill" style={{ background: '#ecfeff', color: '#0f766e' }}>
                                Медиа
                              </span>
                            )}
                            {item.requires_attention && (
                              <span className="pill" style={{ background: '#fef2f2', color: '#b91c1c' }}>
                                Нужна реакция
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: 14, color: 'var(--text-main)', lineHeight: 1.45 }}>
                            {item.summary || item.body}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 8 }}>
                            {formatDate(item.happened_at)}
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-soft)' }}>По этому профилю пока нет привязанных сообщений.</div>
          )}
        </div>
      </div>

      {user.media_items && user.media_items.length > 0 && (
        <div className="screen-section">
          <MediaGallery items={user.media_items} title="Медиа пользователя" />
        </div>
      )}

      {user.permissions.can_view_internal_notes && (
        <>
          <div className="screen-section">
            <div className="glass-card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
                <div>
                  <div className="section-title" style={{ marginBottom: 4 }}>Подписка и комментарии</div>
                  <div className="section-subtitle">Внутренние заметки и наблюдения по профилю.</div>
                </div>
                {!user.permissions.is_self && (
                  <button
                    onClick={toggleWatch}
                    disabled={saving}
                    className="filter-chip active"
                    style={{
                      background: user.is_watching ? 'linear-gradient(135deg, #b45309, #d97706)' : 'linear-gradient(135deg, #0f766e, #0ea5a4)',
                      opacity: saving ? 0.7 : 1,
                    }}
                  >
                    {user.is_watching ? 'Не следить' : 'Следить'}
                  </button>
                )}
              </div>
              <textarea
                value={noteText}
                onChange={(event) => setNoteText(event.target.value)}
                placeholder="Например: быстро отвечает по доставке, нужен follow-up по инструкции, хорошо ведет фотоотчеты."
                style={{
                  width: '100%',
                  minHeight: 112,
                  borderRadius: 18,
                  border: '1px solid rgba(148,163,184,0.22)',
                  background: 'rgba(248,250,252,0.92)',
                  padding: '14px',
                  fontSize: 14,
                  outline: 'none',
                  resize: 'vertical',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
                <button
                  onClick={submitNote}
                  disabled={saving || !noteText.trim()}
                  className="filter-chip active"
                  style={{ opacity: saving || !noteText.trim() ? 0.65 : 1 }}
                >
                  Сохранить комментарий
                </button>
              </div>
            </div>
          </div>

          <div className="screen-section">
            <div className="glass-card" style={{ padding: 16 }}>
              <div className="section-title" style={{ marginBottom: 10 }}>История комментариев</div>
              {user.notes && user.notes.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {user.notes.map((note) => (
                    <div key={note.id} className="soft-card" style={{ padding: '13px 13px 12px' }}>
                      <div style={{ fontSize: 14, color: 'var(--text-main)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                        {note.body}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 8 }}>
                        {note.author_name || 'Система'} · {formatDate(note.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: 'var(--text-soft)' }}>По этому профилю пока нет внутренних комментариев.</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
