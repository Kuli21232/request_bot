import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  addProfileNote,
  getTeamUser,
  type TeamUser,
  unwatchProfile,
  watchProfile,
} from '../api/client'
import { Loader } from '../components/Loader'

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
  const [user, setUser] = useState<TeamUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [noteText, setNoteText] = useState('')
  const [saving, setSaving] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await getTeamUser(Number(id))
      setUser(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const toggleWatch = async () => {
    if (!user) return
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
    if (!user || !noteText.trim()) return
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
              Подписчиков: {user.watchers_count ?? 0}
            </span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>
              Активность: {formatDate(user.last_active_at)}
            </span>
          </div>
        </div>
      </div>

      <div className="screen-section">
        <div className="glass-card" style={{ padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
            <div>
              <div className="section-title" style={{ marginBottom: 4 }}>Подписка и заметки</div>
              <div className="section-subtitle">Следите за профилем и оставляйте внутренние комментарии прямо из mini app.</div>
            </div>
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
          </div>
          <textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Например: лучше писать утром, быстро отвечает по доставке, нужен follow-up по обучению."
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
              Сохранить заметку
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
            <div style={{ color: 'var(--text-soft)' }}>По этому профилю пока нет комментариев.</div>
          )}
        </div>
      </div>
    </div>
  )
}
