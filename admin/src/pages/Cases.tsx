import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { flowApi, type FlowCase } from '../api/client'
import { Loader } from '../components/Loader'

const CASE_STATUSES = ['open', 'watching', 'resolved']

export function Cases() {
  const [cases, setCases] = useState<FlowCase[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)

  const fetchCases = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await flowApi.listCases({ page: 1, page_size: 50 })
      setCases(data.items ?? [])
    } catch {
      setCases([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCases()
  }, [fetchCases])

  const changeStatus = async (id: number, status: string) => {
    setBusyId(id)
    try {
      await flowApi.changeCaseStatus(id, status)
      setCases((prev) => prev.map((item) => (item.id === id ? { ...item, status } : item)))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800">AI-кейсы</h2>
          <p className="text-sm text-slate-500 mt-0.5">Сгруппированные проблемы, повторяющиеся сигналы и длинные цепочки</p>
        </div>
        <button
          onClick={fetchCases}
          className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <RefreshCw className="w-4 h-4" />
          Обновить
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {loading ? (
          <div className="col-span-full flex items-center justify-center h-64 bg-white rounded-xl border border-slate-100"><Loader size="lg" /></div>
        ) : cases.length === 0 ? (
          <div className="col-span-full flex items-center justify-center h-64 bg-white rounded-xl border border-slate-100 text-slate-400">Кейсы пока не сформированы</div>
        ) : (
          cases.map((flowCase) => (
            <div key={flowCase.id} className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    {flowCase.is_critical && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                        <AlertTriangle className="w-3 h-3" /> Критичный
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">{flowCase.kind}</span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">{flowCase.priority}</span>
                  </div>
                  <h3 className="text-base font-semibold text-slate-800">{flowCase.title}</h3>
                  {flowCase.summary && <p className="text-sm text-slate-500 mt-1">{flowCase.summary}</p>}
                </div>
                <div className="text-right text-xs text-slate-400">
                  <div>{flowCase.signal_count} сигналов</div>
                  <div>{flowCase.media_count} медиа</div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap mb-4 text-xs text-slate-500">
                {flowCase.department_name && <span>{flowCase.department_name}</span>}
                {flowCase.stores_affected?.length ? <span>Точек: {flowCase.stores_affected.join(', ')}</span> : null}
                {flowCase.last_signal_at && <span>Последний сигнал: {new Date(flowCase.last_signal_at).toLocaleString('ru-RU')}</span>}
              </div>

              <div className="flex items-center gap-2">
                {CASE_STATUSES.map((status) => (
                  <button
                    key={status}
                    onClick={() => changeStatus(flowCase.id, status)}
                    disabled={busyId === flowCase.id}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      flowCase.status === status ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    } ${busyId === flowCase.id ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
