import { useEffect, useState } from 'react'
import { topicsApi, type Topic } from '../api/client'
import { Loader } from '../components/Loader'

export function Topics() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    topicsApi.list()
      .then((res) => setTopics(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader size="lg" /></div>
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Топики</h2>
        <p className="text-sm text-slate-500 mt-0.5">Автосинхронизированный реестр Telegram topics и AI-профилей</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {topics.map((topic) => (
          <div key={topic.id} className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{topic.icon_emoji || '🧵'}</span>
                  <h3 className="text-base font-semibold text-slate-800">{topic.title}</h3>
                </div>
                <p className="text-sm text-slate-500">thread #{topic.telegram_topic_id} · {topic.topic_kind}</p>
              </div>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                v{topic.profile_version}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-sm mb-4">
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-slate-400 text-xs">Сообщений</div>
                <div className="text-slate-800 font-semibold">{topic.message_count}</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-slate-400 text-xs">Сигналов</div>
                <div className="text-slate-800 font-semibold">{topic.signal_count}</div>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <div className="text-slate-400 text-xs">Медиа</div>
                <div className="text-slate-800 font-semibold">{topic.media_count}</div>
              </div>
            </div>

            {topic.profile && (
              <div className="space-y-2 text-sm">
                <div><span className="text-slate-400">Профиль:</span> <span className="text-slate-700">{topic.profile.profile_summary || 'Без описания'}</span></div>
                <div><span className="text-slate-400">Типы:</span> <span className="text-slate-700">{topic.profile.allowed_signal_types.join(', ')}</span></div>
                <div><span className="text-slate-400">Fallback:</span> <span className="text-slate-700">{topic.profile.default_actions?.fallback || '—'}</span></div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
