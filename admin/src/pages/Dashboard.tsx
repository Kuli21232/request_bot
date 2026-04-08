import { useState, useEffect, useCallback } from 'react'
import { Inbox, Clock, CheckCircle, AlertTriangle, LayoutGrid, RefreshCw, Users, Radio } from 'lucide-react'
import { analyticsApi, flowApi, type AnalyticsOverview, type VolumeDay, type DepartmentStat, type AgentStat, type DigestOverview } from '../api/client'
import { StatCard } from '../components/StatCard'
import { Loader } from '../components/Loader'

const AUTO_REFRESH_MS = 30_000

export function Dashboard() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [digest, setDigest] = useState<DigestOverview | null>(null)
  const [volume, setVolume] = useState<VolumeDay[]>([])
  const [deptStats, setDeptStats] = useState<DepartmentStat[]>([])
  const [agents, setAgents] = useState<AgentStat[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setIsLoading(true)
    else setRefreshing(true)
    try {
      const [ovRes, volRes, deptRes, agentRes, digestRes] = await Promise.allSettled([
        analyticsApi.overview(),
        analyticsApi.volume(30),
        analyticsApi.byDepartment(),
        analyticsApi.agents(),
        flowApi.digestOverview(),
      ])
      if (ovRes.status === 'fulfilled') setOverview(ovRes.value.data)
      if (volRes.status === 'fulfilled') setVolume(volRes.value.data)
      if (deptRes.status === 'fulfilled') setDeptStats(deptRes.value.data)
      if (agentRes.status === 'fulfilled') setAgents(agentRes.value.data)
      if (digestRes.status === 'fulfilled') setDigest(digestRes.value.data)
      setLastUpdated(new Date())
    } finally {
      setIsLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(() => fetchData(true), AUTO_REFRESH_MS)
    return () => clearInterval(interval)
  }, [fetchData])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Обзор инфопотока</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Сигналы, кейсы и теневые заявки
            {lastUpdated && <> · Обновлено в {lastUpdated.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</>}
          </p>
        </div>
        <button
          onClick={() => fetchData(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-60"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Обновить
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="Сигналы" value={digest?.total_signals ?? 0} icon={<Radio className="w-5 h-5" />} iconBg="bg-indigo-500" subtitle="Всего в потоке" />
        <StatCard title="Внимание" value={digest?.requires_attention ?? 0} icon={<AlertTriangle className="w-5 h-5" />} iconBg="bg-rose-500" subtitle="Требуют реакции" />
        <StatCard title="Кейсы" value={digest?.critical_cases ?? 0} icon={<Users className="w-5 h-5" />} iconBg="bg-emerald-500" subtitle="Критичные кейсы" />
        <StatCard title="Медиа" value={digest?.with_media ?? 0} icon={<LayoutGrid className="w-5 h-5" />} iconBg="bg-cyan-500" subtitle="Фото и видео" />
        <StatCard title="Шум" value={digest?.noise ?? 0} icon={<Clock className="w-5 h-5" />} iconBg="bg-slate-500" subtitle="Digest only" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="Новые заявки" value={overview?.new ?? 0} icon={<Inbox className="w-5 h-5" />} iconBg="bg-blue-500" subtitle="Shadow tickets" />
        <StatCard title="В работе" value={overview?.in_progress ?? 0} icon={<Clock className="w-5 h-5" />} iconBg="bg-yellow-500" subtitle="Команда обрабатывает" />
        <StatCard title="Решены" value={overview?.resolved ?? 0} icon={<CheckCircle className="w-5 h-5" />} iconBg="bg-green-500" subtitle="Закрытые заявки" />
        <StatCard title="SLA" value={overview?.sla_breached ?? 0} icon={<AlertTriangle className="w-5 h-5" />} iconBg="bg-red-500" subtitle="Просрочено" />
        <StatCard title="Всего" value={overview?.total ?? 0} icon={<LayoutGrid className="w-5 h-5" />} iconBg="bg-slate-600" subtitle="Наследный слой" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 lg:col-span-2">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Топ типов сигналов</h3>
          <div className="space-y-3">
            {(digest?.top_kinds ?? []).map((item) => (
              <div key={item.kind} className="flex items-center gap-3">
                <div className="w-28 text-sm text-slate-600 truncate">{item.kind}</div>
                <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{ width: `${Math.max(8, (item.count / Math.max(...(digest?.top_kinds ?? [{ count: 1 }]).map((row) => row.count), 1)) * 100)}%` }}
                  />
                </div>
                <div className="w-10 text-right text-sm font-semibold text-slate-800">{item.count}</div>
              </div>
            ))}
            {!digest?.top_kinds?.length && <div className="text-sm text-slate-400">Пока нет данных по типам сигналов</div>}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Контекст</h3>
          <div className="space-y-3 text-sm text-slate-600">
            <div>Отделов в аналитике: <span className="font-semibold text-slate-800">{deptStats.length}</span></div>
            <div>Активных агентов: <span className="font-semibold text-slate-800">{agents.length}</span></div>
            <div>Дней в окне объёма: <span className="font-semibold text-slate-800">{volume.length}</span></div>
            <div>Средняя оценка: <span className="font-semibold text-slate-800">{overview?.avg_satisfaction?.toFixed(1) ?? '—'}</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}
