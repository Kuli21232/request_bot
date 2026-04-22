import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteTopic, getTopics, updateTopicMeta, type Topic } from '../api/client'
import { Loader } from '../components/Loader'
import {
  getRecommendedActionLabel,
  getSignalKindHint,
  getSignalKindLabel,
  getTopicDisplayTitle,
  getTopicKindLabel,
  getTopicSummary,
} from '../utils/flow'

export default function Topics() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [openMenu, setOpenMenu] = useState<number | null>(null)
  const [editing, setEditing] = useState<Topic | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editEmoji, setEditEmoji] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getTopics()
      .then(setTopics)
      .finally(() => setLoading(false))
  }, [])

  const grouped = useMemo(() => {
    const groups = new Map<number, { title: string; topics: Topic[] }>()
    for (const topic of topics) {
      const entry = groups.get(topic.group_id) ?? { title: topic.group_title || `Группа ${topic.group_id}`, topics: [] }
      entry.topics.push(topic)
      groups.set(topic.group_id, entry)
    }
    return Array.from(groups.values()).map((entry) => ({
      title: entry.title,
      topics: entry.topics.sort((a, b) => new Date(b.last_seen_at || 0).getTime() - new Date(a.last_seen_at || 0).getTime()),
    }))
  }, [topics])

  const startEdit = (topic: Topic) => {
    setEditing(topic)
    setEditTitle(topic.title)
    setEditEmoji(topic.icon_emoji || '')
    setOpenMenu(null)
  }

  const saveEdit = async () => {
    if (!editing) return
    const title = editTitle.trim()
    if (!title) return
    setSaving(true)
    try {
      const updated = await updateTopicMeta(editing.id, {
        title,
        icon_emoji: editEmoji.trim() || null,
      })
      setTopics((prev) => prev.map((t) => (t.id === updated.id ? { ...t, ...updated } : t)))
      setEditing(null)
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async (topic: Topic) => {
    setOpenMenu(null)
    if (!window.confirm(`Убрать топик «${getTopicDisplayTitle(topic)}» из списка?\n\nИстория и сигналы сохранятся, но топик перестанет показываться.`)) {
      return
    }
    await deleteTopic(topic.id)
    setTopics((prev) => prev.filter((t) => t.id !== topic.id))
  }

  if (loading) {
    return <div style={{ padding: '40px 0' }}><Loader /></div>
  }

  return (
    <div className="app-shell" onClick={() => setOpenMenu(null)}>
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Разделы по топикам</div>
          <div className="section-subtitle">
            Каждый топик — отдельная тема в чате. Можно переименовать или скрыть лишние.
          </div>
        </div>
      </div>

      <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {grouped.map((group, index) => (
          <div key={`${group.title}-${index}`} className="glass-card" style={{ padding: '14px 14px 13px' }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)', marginBottom: 10 }}>
              {group.title}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {group.topics.map((topic) => (
                <div key={topic.id} className="soft-card" style={{ padding: '14px 14px 13px', position: 'relative' }}>
                  <Link to={`/topics/${topic.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 7, paddingRight: 28 }}>
                      <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.25 }}>
                        {topic.icon_emoji || '🧵'} {getTopicDisplayTitle(topic)}
                      </div>
                      <span
                        className="pill"
                        style={{ background: '#eff6ff', color: '#1d4ed8', flexShrink: 0, alignSelf: 'flex-start' }}
                        title="Роль топика в общем потоке"
                      >
                        {getTopicKindLabel(topic.topic_kind)}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 10 }}>
                      {getTopicSummary(topic)}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: topic.profile?.allowed_signal_types.length ? 10 : 0 }}>
                      <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }} title="Всего сообщений в топике">
                        Сообщ.: {topic.message_count}
                      </span>
                      <span className="pill" style={{ background: '#ecfdf5', color: '#0f766e' }} title="Сколько из них ИИ уже разобрал">
                        Разобрано: {topic.signal_count}
                      </span>
                      <span className="pill" style={{ background: '#ecfeff', color: '#155e75' }} title="Фото / видео / документы">
                        Медиа: {topic.media_count}
                      </span>
                      {topic.profile?.automation?.recommended_action && (
                        <span
                          className="pill"
                          style={{ background: '#fefce8', color: '#854d0e' }}
                          title="Что ИИ предлагает сделать с этим топиком"
                        >
                          {getRecommendedActionLabel(topic.profile.automation.recommended_action)}
                        </span>
                      )}
                    </div>
                    {topic.profile && topic.profile.allowed_signal_types.length > 0 && (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {topic.profile.allowed_signal_types.slice(0, 5).map((item) => (
                          <span
                            key={item}
                            className="pill"
                            style={{ background: '#fff7ed', color: '#9a3412' }}
                            title={getSignalKindHint(item) || 'Тип сообщений, которые ждём в этом топике'}
                          >
                            {getSignalKindLabel(item)}
                          </span>
                        ))}
                      </div>
                    )}
                  </Link>

                  <button
                    type="button"
                    aria-label="Действия с топиком"
                    onClick={(e) => {
                      e.stopPropagation()
                      setOpenMenu(openMenu === topic.id ? null : topic.id)
                    }}
                    style={{
                      position: 'absolute',
                      top: 10,
                      right: 10,
                      width: 28,
                      height: 28,
                      borderRadius: 8,
                      border: 'none',
                      background: 'transparent',
                      cursor: 'pointer',
                      color: 'var(--text-soft)',
                      fontSize: 20,
                      lineHeight: 1,
                      padding: 0,
                    }}
                  >
                    ⋯
                  </button>

                  {openMenu === topic.id && (
                    <div
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        position: 'absolute',
                        top: 38,
                        right: 10,
                        background: '#fff',
                        borderRadius: 12,
                        boxShadow: '0 12px 32px rgba(15,23,42,0.18)',
                        border: '1px solid var(--line)',
                        padding: 6,
                        zIndex: 10,
                        minWidth: 170,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => startEdit(topic)}
                        style={menuItemStyle}
                      >
                        ✏️ Переименовать
                      </button>
                      <button
                        type="button"
                        onClick={() => confirmDelete(topic)}
                        style={{ ...menuItemStyle, color: '#b91c1c' }}
                      >
                        🗑 Скрыть топик
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {editing && (
        <div
          onClick={() => !saving && setEditing(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15,23,42,0.5)',
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: 520,
              background: '#fff',
              borderTopLeftRadius: 20,
              borderTopRightRadius: 20,
              padding: '18px 18px 22px',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-main)' }}>
              Переименовать топик
            </div>
            <div>
              <label style={inputLabelStyle}>Название</label>
              <input
                autoFocus
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="Например, «Южный филиал — логистика»"
                style={inputStyle}
              />
            </div>
            <div>
              <label style={inputLabelStyle}>Эмодзи (необязательно)</label>
              <input
                value={editEmoji}
                onChange={(e) => setEditEmoji(e.target.value.slice(0, 4))}
                placeholder="🚚"
                style={inputStyle}
              />
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
              <button
                type="button"
                onClick={() => setEditing(null)}
                disabled={saving}
                style={{ ...btnStyle, background: '#f1f5f9', color: 'var(--text-main)' }}
              >
                Отмена
              </button>
              <button
                type="button"
                onClick={saveEdit}
                disabled={saving || !editTitle.trim()}
                style={{ ...btnStyle, background: 'var(--brand)', color: '#fff', opacity: saving ? 0.7 : 1 }}
              >
                {saving ? 'Сохраняем…' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const menuItemStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  textAlign: 'left',
  padding: '9px 12px',
  border: 'none',
  background: 'transparent',
  borderRadius: 8,
  fontSize: 14,
  color: 'var(--text-main)',
  cursor: 'pointer',
}

const inputLabelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  color: 'var(--text-soft)',
  marginBottom: 6,
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 12,
  border: '1px solid rgba(148,163,184,0.3)',
  fontSize: 15,
  background: '#fff',
  outline: 'none',
  boxSizing: 'border-box',
}

const btnStyle: React.CSSProperties = {
  flex: 1,
  padding: '12px 16px',
  borderRadius: 12,
  border: 'none',
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
}
