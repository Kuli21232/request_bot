import type { ReactNode } from 'react'

interface StatCardProps {
  title: string
  value: number | string
  icon: ReactNode
  iconBg: string
  change?: string
  changeType?: 'up' | 'down' | 'neutral'
  subtitle?: string
}

export function StatCard({ title, value, icon, iconBg, change, changeType, subtitle }: StatCardProps) {
  const changeColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-slate-500',
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 flex items-start gap-4 hover:shadow-md transition-shadow">
      <div className={`${iconBg} p-3 rounded-xl flex-shrink-0`}>
        <div className="text-white w-6 h-6 flex items-center justify-center">
          {icon}
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-slate-500 text-sm font-medium truncate">{title}</p>
        <p className="text-2xl font-bold text-slate-800 mt-0.5 leading-tight">{value}</p>
        {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        {change && (
          <p className={`text-xs mt-1 ${changeColors[changeType || 'neutral']}`}>
            {change}
          </p>
        )}
      </div>
    </div>
  )
}
