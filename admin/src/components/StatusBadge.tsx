import type { RequestStatus, RequestPriority } from '../api/client'

const statusConfig: Record<RequestStatus, { label: string; className: string }> = {
  new: { label: 'Новый', className: 'bg-blue-100 text-blue-700 border border-blue-200' },
  open: { label: 'Открыт', className: 'bg-indigo-100 text-indigo-700 border border-indigo-200' },
  in_progress: { label: 'В работе', className: 'bg-yellow-100 text-yellow-700 border border-yellow-200' },
  waiting_for_user: { label: 'Ожидание', className: 'bg-orange-100 text-orange-700 border border-orange-200' },
  resolved: { label: 'Решён', className: 'bg-green-100 text-green-700 border border-green-200' },
  closed: { label: 'Закрыт', className: 'bg-slate-100 text-slate-600 border border-slate-200' },
}

const priorityConfig: Record<RequestPriority, { label: string; className: string }> = {
  low: { label: 'Низкий', className: 'bg-slate-100 text-slate-600 border border-slate-200' },
  normal: { label: 'Обычный', className: 'bg-blue-100 text-blue-700 border border-blue-200' },
  high: { label: 'Высокий', className: 'bg-orange-100 text-orange-700 border border-orange-200' },
  critical: { label: 'Критичный', className: 'bg-red-100 text-red-700 border border-red-200' },
}

interface StatusBadgeProps {
  status: RequestStatus
  onClick?: () => void
  small?: boolean
}

export function StatusBadge({ status, onClick, small = false }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: 'bg-slate-100 text-slate-600' }
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${small ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-0.5 text-xs'} ${config.className} ${onClick ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}`}
      onClick={onClick}
    >
      {config.label}
    </span>
  )
}

interface PriorityBadgeProps {
  priority: RequestPriority
  small?: boolean
}

export function PriorityBadge({ priority, small = false }: PriorityBadgeProps) {
  const config = priorityConfig[priority] || { label: priority, className: 'bg-slate-100 text-slate-600' }
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${small ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-0.5 text-xs'} ${config.className}`}
    >
      {config.label}
    </span>
  )
}

export { statusConfig, priorityConfig }
