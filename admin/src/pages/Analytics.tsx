import { useState, useEffect } from 'react'
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
  RadialBarChart,
  RadialBar,
} from 'recharts'
import { analyticsApi, type AnalyticsOverview, type VolumeDay, type DepartmentStat, type SlaStat, type AgentStat, type MyStats } from '../api/client'
import { Loader } from '../components/Loader'
import { CheckCircle, TrendingUp, Users, Star } from 'lucide-react'

const DEPT_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899']

export function Analytics() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [volume, setVolume] = useState<VolumeDay[]>([])
  const [deptStats, setDeptStats] = useState<DepartmentStat[]>([])
  const [slaStat, setSlaStat] = useState<SlaStat | null>(null)
  const [agents, setAgents] = useState<AgentStat[]>([])
  const [myStats, setMyStats] = useState<MyStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [days, setDays] = useState(30)

  useEffect(() => {
    setIsLoading(true)
    Promise.allSettled([
      analyticsApi.overview(),
      analyticsApi.volume(days),
      analyticsApi.byDepartment(),
      analyticsApi.sla(),
      analyticsApi.agents(),
      analyticsApi.myStats(),
    ]).then(([ovRes, volRes, deptRes, slaRes, agentRes, myRes]) => {
      if (ovRes.status === 'fulfilled') setOverview(ovRes.value.data)
      if (volRes.status === 'fulfilled') setVolume(volRes.value.data)
      if (deptRes.status === 'fulfilled') setDeptStats(deptRes.value.data)
      if (slaRes.status === 'fulfilled') setSlaStat(slaRes.value.data)
      if (agentRes.status === 'fulfilled') setAgents(agentRes.value.data)
      if (myRes.status === 'fulfilled') setMyStats(myRes.value.data)
    }).finally(() => setIsLoading(false))
  }, [days])

  const formattedVolume = volume.map((d) => ({
    ...d,
    label: new Date(d.day).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }),
  }))

  interface TooltipProps {
    active?: boolean
    payload?: Array<{ value: number; name: string }>
    label?: string
  }

  const VolumeTooltip = ({ active, payload, label }: TooltipProps) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg px-3 py-2">
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-semibold text-blue-600">{payload[0].value} заявок</p>
      </div>
    )
  }

  const PieTooltipComp = ({ active, payload }: TooltipProps) => {
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

  const slaData = slaStat
    ? [
        { name: 'В срок', value: slaStat.compliance_percent, fill: '#10b981' },
      ]
    : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Аналитика</h2>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value={7}>7 дней</option>
          <option value={14}>14 дней</option>
          <option value={30}>30 дней</option>
          <option value={90}>90 дней</option>
        </select>
      </div>

      {/* My stats */}
      {myStats && (
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-5 text-white shadow-lg shadow-blue-500/20">
          <h3 className="text-sm font-semibold opacity-80 mb-3 flex items-center gap-2">
            <Star className="w-4 h-4" /> Мои показатели
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-2xl font-bold">{myStats.total_assigned}</p>
              <p className="text-xs opacity-70 mt-0.5">Всего назначено</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{myStats.open_requests}</p>
              <p className="text-xs opacity-70 mt-0.5">Открытых сейчас</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{myStats.resolved_today}</p>
              <p className="text-xs opacity-70 mt-0.5">Решено сегодня</p>
            </div>
            <div>
              <p className="text-2xl font-bold">
                {myStats.avg_response_time != null
                  ? `${Math.round(myStats.avg_response_time)}м`
                  : '—'}
              </p>
              <p className="text-xs opacity-70 mt-0.5">Ср. время ответа</p>
            </div>
          </div>
        </div>
      )}

      {/* Volume chart */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
        <h3 className="text-base font-semibold text-slate-800 mb-1 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-slate-400" />
          Объём заявок
        </h3>
        <p className="text-xs text-slate-400 mb-4">За последние {days} дней</p>
        {formattedVolume.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
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
          <div className="h-52 flex items-center justify-center text-slate-400 text-sm">Нет данных</div>
        )}
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* By department */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">По отделам</h3>
          {deptStats.length > 0 ? (
            <>
              <PieChart width={160} height={160} className="mx-auto">
                <Pie
                  data={deptStats.map((d) => ({ name: `${d.emoji || ''} ${d.department}`, value: d.count }))}
                  cx={75}
                  cy={75}
                  innerRadius={45}
                  outerRadius={72}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {deptStats.map((_, idx) => (
                    <Cell key={idx} fill={DEPT_COLORS[idx % DEPT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltipComp />} />
              </PieChart>
              <div className="space-y-2 mt-3">
                {deptStats.map((d, idx) => (
                  <div key={d.department} className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: DEPT_COLORS[idx % DEPT_COLORS.length] }} />
                    <span className="text-xs text-slate-600 truncate flex-1">{d.emoji} {d.department}</span>
                    <span className="text-xs font-semibold text-slate-800">{d.count}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm">Нет данных</div>
          )}
        </div>

        {/* SLA */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-slate-400" /> SLA
          </h3>
          {slaStat ? (
            <div className="space-y-4">
              <div className="flex flex-col items-center">
                <RadialBarChart
                  width={140}
                  height={140}
                  cx={70}
                  cy={70}
                  innerRadius={45}
                  outerRadius={65}
                  data={slaData}
                  startAngle={90}
                  endAngle={-270}
                >
                  <RadialBar
                    background={{ fill: '#f1f5f9' }}
                    dataKey="value"
                    cornerRadius={8}
                    fill="#10b981"
                  />
                  <text x={70} y={65} textAnchor="middle" dominantBaseline="middle" className="font-bold text-slate-800">
                    <tspan x="70" dy="0" fontSize="22" fontWeight="bold" fill="#1e293b">
                      {Math.round(slaStat.compliance_percent)}%
                    </tspan>
                    <tspan x="70" dy="18" fontSize="11" fill="#94a3b8">соблюдение</tspan>
                  </text>
                </RadialBarChart>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <p className="text-lg font-bold text-green-600">{slaStat.on_time}</p>
                  <p className="text-xs text-green-500 mt-0.5">В срок</p>
                </div>
                <div className="bg-red-50 rounded-lg p-3 text-center">
                  <p className="text-lg font-bold text-red-500">{slaStat.breached}</p>
                  <p className="text-xs text-red-400 mt-0.5">Просрочено</p>
                </div>
              </div>
              <p className="text-xs text-center text-slate-400">Всего с SLA: {slaStat.total_with_sla}</p>
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm">Нет данных</div>
          )}
        </div>

        {/* Agents */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-400" /> Нагрузка агентов
          </h3>
          {agents.length > 0 ? (
            <div className="space-y-3">
              {agents.slice(0, 6).map((agent, idx) => {
                const max = Math.max(...agents.map((a) => a.open_count), 1)
                const pct = Math.round((agent.open_count / max) * 100)
                return (
                  <div key={agent.username || idx}>
                    <div className="flex justify-between items-center mb-1">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-slate-200 rounded-full flex items-center justify-center flex-shrink-0">
                          <span className="text-slate-600 text-xs font-medium">{agent.name.charAt(0).toUpperCase()}</span>
                        </div>
                        <span className="text-xs text-slate-700 truncate max-w-28">{agent.name}</span>
                      </div>
                      <span className="text-xs font-semibold text-slate-800">{agent.open_count}</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          background: pct > 80 ? '#ef4444' : pct > 50 ? '#f59e0b' : '#3b82f6',
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm">Нет данных</div>
          )}
        </div>
      </div>

      {/* Overview summary */}
      {overview && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Общая статистика</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { label: 'Всего', value: overview.total, color: 'text-slate-800' },
              { label: 'Новых', value: overview.new, color: 'text-blue-600' },
              { label: 'В работе', value: overview.in_progress, color: 'text-yellow-600' },
              { label: 'Решено', value: overview.resolved, color: 'text-green-600' },
              { label: 'Просрочено', value: overview.sla_breached, color: 'text-red-600' },
              {
                label: 'Оценка',
                value: overview.avg_satisfaction != null ? overview.avg_satisfaction.toFixed(1) : '—',
                color: 'text-amber-600',
              },
            ].map((item) => (
              <div key={item.label} className="text-center p-3 bg-slate-50 rounded-lg">
                <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
                <p className="text-xs text-slate-500 mt-1">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
