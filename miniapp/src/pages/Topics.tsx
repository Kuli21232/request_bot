import { useEffect, useState } from 'react'
import { getTopics, type Topic } from '../api/client'
import { Loader } from '../components/Loader'

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
    <div style={{ padding: '12px 12px 88px' }}>
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Топики</div>
        <div style={{ fontSize: 12, color: '#94a3b8' }}>AI видит их автоматически и строит профиль поведения</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {topics.map((topic) => (
          <div key={topic.id} style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 16, padding: '14px 15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{topic.icon_emoji || '🧵'} {topic.title}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>{topic.topic_kind}</div>
            </div>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
              thread #{topic.telegram_topic_id} · сообщений {topic.message_count} · сигналов {topic.signal_count}
            </div>
            {topic.profile && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {topic.profile.allowed_signal_types.slice(0, 4).map((item) => (
                  <span key={item} style={{ fontSize: 11, background: '#e2e8f0', color: '#334155', borderRadius: 100, padding: '2px 8px' }}>{item}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
