import { useEffect, useState } from 'react'
import { getTopics, type Topic } from '../api/client'
import { Loader } from '../components/Loader'
import { getSignalKindLabel, getTopicKindLabel, getTopicSummary } from '../utils/flow'

export default function Topics() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTopics()
      .then(setTopics)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div style={{ padding: '40px 0' }}><Loader /></div>
  }

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Темы Telegram</div>
          <div className="section-subtitle">
            Все топики группы появляются здесь автоматически. Система смотрит, о чем в них чаще пишут, и подстраивает разбор потока.
          </div>
        </div>
      </div>

      <div className="screen-section" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {topics.map((topic) => (
          <div key={topic.id} className="glass-card" style={{ padding: '15px 15px 14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 7 }}>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-main)' }}>
                {topic.icon_emoji || '🧵'} {topic.title}
              </div>
              <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getTopicKindLabel(topic.topic_kind)}</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.45, marginBottom: 10 }}>
              {getTopicSummary(topic)}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
              <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>Сообщений: {topic.message_count}</span>
              <span className="pill" style={{ background: '#ecfdf5', color: '#0f766e' }}>Разобрано: {topic.signal_count}</span>
              <span className="pill" style={{ background: '#ecfeff', color: '#155e75' }}>Медиа: {topic.media_count}</span>
            </div>
            {topic.profile && topic.profile.allowed_signal_types.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {topic.profile.allowed_signal_types.slice(0, 4).map((item) => (
                  <span key={item} className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>{getSignalKindLabel(item)}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
