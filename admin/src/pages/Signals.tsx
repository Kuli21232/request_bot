import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Camera, Search } from 'lucide-react'
import { flowApi, type FlowSignal } from '../api/client'
import { Loader } from '../components/Loader'

function importanceColor(value: string) {
  if (value === 'critical') return 'bg-red-100 text-red-700'
  if (value === 'high') return 'bg-orange-100 text-orange-700'
  if (value === 'low') return 'bg-slate-100 text-slate-600'
  return 'bg-blue-100 text-blue-700'
}

export function Signals() {
  const [signals, setSignals] = useState<FlowSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [attentionOnly, setAttentionOnly] = useState(false)

  const fetchSignals = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await flowApi.listSignals({
        page: 1,
        page_size: 50,
        ...(search ? { search } : {}),
        ...(attentionOnly ? { requires_attention: true } : {}),
      })
      setSignals(data.items ?? [])
    } catch {
      setSignals([])
    } finally {
      setLoading(false)
    }
  }, [search, attentionOnly])

  useEffect(() => {
    fetchSignals()
  }, [fetchSignals])

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск по сигналам, точкам и темам"
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={attentionOnly}
              onChange={(e) => setAttentionOnly(e.target.checked)}
              className="w-4 h-4"
            />
            <AlertTriangle className="w-4 h-4 text-red-500" />
            Только требующие реакции
          </label>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64"><Loader size="lg" /></div>
        ) : signals.length === 0 ? (
          <div className="flex items-center justify-center h-64 text-slate-400">Сигналы не найдены</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {signals.map((signal) => (
              <div key={signal.id} className="p-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{signal.kind}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${importanceColor(signal.importance)}`}>{signal.importance}</span>
                      {signal.has_media && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-cyan-100 text-cyan-700">
                          <Camera className="w-3 h-3" /> Медиа
                        </span>
                      )}
                      {signal.case_title && (
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                          {signal.case_title}
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-slate-800 mb-1">{signal.summary || signal.body}</div>
                    <div className="text-sm text-slate-500 line-clamp-2">{signal.body}</div>
                    <div className="flex items-center gap-2 flex-wrap mt-3 text-xs text-slate-500">
                      {signal.store && <span>{signal.store}</span>}
                      {signal.department_name && <span>{signal.department_name}</span>}
                      {signal.recommended_action && <span>Рекомендация: {signal.recommended_action}</span>}
                    </div>
                  </div>
                  <div className="text-xs text-slate-400 whitespace-nowrap">
                    {new Date(signal.happened_at).toLocaleString('ru-RU')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
