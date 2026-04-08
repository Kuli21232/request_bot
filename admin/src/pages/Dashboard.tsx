import { useState, useEffect, useCallback } from 'react'
import {
  Inbox,
  Clock,
  CheckCircle,
  AlertTriangle,
  LayoutGrid,
  Star,
  RefreshCw,
  Users,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { analyticsApi, type AnalyticsOverview, type VolumeDay, type DepartmentStat, type AgentStat } from '../api/client'
import { StatCard } from '../components/StatCard'
import { Loader } from '../components/Loader'

const DEPT_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899']

const AUTO_REFRESH_MS = 30_000

export function Dashboard() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
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
      const [ovRes, volRes, deptRes, agentRes] = await Promise.allSettled([
        analyticsApi.overview(),
        analyticsApi.volume(30),
        analyticsApi.byDepartment(),
        analyticsApi.agents(),
      ])
      if (ovRes.status === 'fulfilled') setOverview(ovRes.value.data)
      if (volRes.status === 'fulfilled') setVolume(volRes.value.data)
      if (deptRes.status === 'fulfilled') setDeptStats(deptRes.value.data)
      if (agentRes.status === 'fulfilled') setAgents(agentRes.value.data)
      setLastUpdated(new Date())
    } catch {
      // handled per-request
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

  const formattedVolume = volume.map((d) => {
    const date = new Date(d.day)
    return {
      ...d,
      label: date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }),
    }
  })

  interface VolumeTooltipPayload {
    value: number
  }
  interface VolumeTooltipProps {
    active?: boolean
    payload?: VolumeTooltipPayload[]
    label?: string
  }

  const VolumeTooltip = ({ active, payload, label }: VolumeTooltipProps) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2">
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-semibold text-blue-600">{payload[0].value} заявок</p>
      </div>
    )
  }

  interface PieTooltipPayload {
    name: string
    value: number
  }
  interface PieTooltipProps {
    active?: boolean
    payload?: PieTooltipPayload[]
  }

  const PieTooltip = ({ active, payload }: PieTooltipProps) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2">
        <p className="text-sm font-medium text-slate-700">{payload[0].name}</p>
        <p className="text-sm text-blue-600">{payload[0].value} заявок</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Обзор системы</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Актуальные данные за сегодня
            {lastUpdated && (
              <> · Обновлено в {lastUpdated.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</>
            )}
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

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Новые"
          value={overview?.new ?? 0}
          icon={<Inbox className="w-5 h-5" />}
          iconBg="bg-blue-500"
          subtitle="Ожидают обработки"
        />
        <StatCard
          title="В работе"
          value={overview?.in_progress ?? 0}
          icon={<Clock className="w-5 h-5" />}
          iconBg="bg-yellow-500"
          subtitle="Активные заявки"
        />
        <StatCard
          title="Решённые"
          value={overview?.resolved ?? 0}
          icon={<CheckCircle className="w-5 h-5" />}
          iconBg="bg-green-500"
          subtitle="Успешно закрыты"
        />
        <StatCard
          title="Просроченные"
          value={overview?.sla_breached ?? 0}
          icon={<AlertTriangle className="w-5 h-5" />}
          iconBg="bg-red-500"
          subtitle="Нарушен SLA"
        />
        <StatCard
          title="Всего"
          value={overview?.total ?? 0}
          icon={<LayoutGrid className="w-5 h-5" />}
          iconBg="bg-slate-600"
          subtitle={
            overview?.avg_satisfaction
              ? `Оценка: ${overview.avg_satisfaction.toFixed(1)} ⭐`
              : 'Все заявки'
          }
        />
      </div>

      {/* Volume chart */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
        <h3 className="text-base font-semibold text-slate-800 mb-4">
          Объём заявок за 30 дней
        </h3>
        {formattedVolume.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={formattedVolume} margin={{ top: 5, right: 10, left: -15, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<VolumeTooltip />} cursor={{ fill: '#f8fafc' }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-52 flex items-center justify-center text-slate-400 text-sm">
            Нет данных
          </div>
        )}
      </div>

      {/* Bottom row: dept + agents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By department */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <LayoutGrid className="w-4 h-4 text-slate-400" />
            По отделам
          </h3>
          {deptStats.length > 0 ? (
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <PieChart width={180} height={180}>
                <Pie
                  data={deptStats.map((d) => ({ name: `${d.emoji || ''} ${d.department}`, value: d.count }))}
                  cx={85}
                  cy={85}
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {deptStats.map((_, idx) => (
                    <Cell key={idx} fill={DEPT_COLORS[idx % DEPT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
              </PieChart>
              <div className="flex-1 space-y-2 min-w-0">
                {deptStats.map((d, idx) => (
                  <div key={d.department} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ background: DEPT_COLORS[idx % DEPT_COLORS.length] }}
                    />
                    <span className="text-sm text-slate-600 truncate flex-1">
                      {d.emoji} {d.department}
                    </span>
                    <span className="text-sm font-semibold text-slate-800 ml-auto">{d.count}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-44 flex items-center justify-center text-slate-400 text-sm">
              Нет данных
            </div>
          )}
        </div>

        {/* Agent workload */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-400" />
            Загрузка сотрудников
          </h3>
          {agents.length > 0 ? (
            <div className="space-y-3">
              {agents.slice(0, 8).map((agent) => {
                const max = Math.max(...agents.map((a) => a.open_count), 1)
                const pct = Math.round((agent.open_count / max) * 100)
                return (
                  <div key={agent.username}>
                    <div className="flex justify-between items-center mb-1">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-slate-200 rounded-full flex items-center justify-center flex-shrink-0">
                          <span className="text-slate-600 text-xs font-medium">
                            {agent.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <span className="text-sm text-slate-700 truncate max-w-40">{agent.name}</span>
                      </div>
                      <span className="text-sm font-semibold text-slate-800 ml-2 flex-shrink-0">
                        {agent.open_count}
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="h-44 flex items-center justify-center text-slate-400 text-sm">
              Нет данных
            </div>
          )}
        </div>
      </div>

      {/* Satisfaction note */}
      {overview?.avg_satisfaction != null && (
        <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-100 rounded-xl p-4 flex items-center gap-3">
          <Star className="w-5 h-5 text-amber-500 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              Средняя оценка удовлетворённости:{' '}
              <span className="font-bold">{overview.avg_satisfaction.toFixed(2)}</span> из 5
            </p>
            <p className="text-xs text-amber-600 mt-0.5">На основе оценок пользователей</p>
          </div>
        </div>
      )}
    </div>
  )
}
