import { useEffect, useMemo, useState } from 'react'
import { getTopics, type Topic } from '../api/client'
import { Loader } from '../components/Loader'
import {
  getRecommendedActionLabel,
  getSignalKindLabel,
  getTopicKindLabel,
  getTopicSummary,
} from '../utils/flow'

export default function Topics() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)

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

  if (loading) {
    return <div style={{ padding: '40px 0' }}><Loader /></div>
  }

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div className="glass-card" style={{ padding: '16px 16px 14px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>Разделы по топикам</div>
          <div className="section-subtitle">
            Все топики собираются автоматически. Для каждого AI хранит краткое понимание темы, рекомендуемое действие и допустимые типы сообщений.
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
                <div key={topic.id} className="soft-card" style={{ padding: '14px 14px 13px' }}>
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
                    {topic.profile?.automation?.recommended_action && (
                      <span className="pill" style={{ background: '#fefce8', color: '#854d0e' }}>
                        {getRecommendedActionLabel(topic.profile.automation.recommended_action)}
                      </span>
                    )}
                  </div>
                  {topic.profile && topic.profile.allowed_signal_types.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {topic.profile.allowed_signal_types.slice(0, 5).map((item) => (
                        <span key={item} className="pill" style={{ background: '#fff7ed', color: '#9a3412' }}>
                          {getSignalKindLabel(item)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
