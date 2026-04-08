const STATUS: Record<string, { label: string; bg: string; color: string; dot: string }> = {
  new:              { label: 'Новая',     bg: '#dbeafe', color: '#1d4ed8', dot: '#3b82f6' },
  open:             { label: 'Открыта',   bg: '#e0e7ff', color: '#4338ca', dot: '#6366f1' },
  in_progress:      { label: 'В работе',  bg: '#fef3c7', color: '#92400e', dot: '#f59e0b' },
  waiting_for_user: { label: 'Ожидание',  bg: '#ffedd5', color: '#c2410c', dot: '#f97316' },
  resolved:         { label: 'Решена',    bg: '#dcfce7', color: '#15803d', dot: '#22c55e' },
  closed:           { label: 'Закрыта',   bg: '#f3f4f6', color: '#6b7280', dot: '#9ca3af' },
  duplicate:        { label: 'Дубликат',  bg: '#f3e8ff', color: '#7e22ce', dot: '#a855f7' },
}

const PRIORITY: Record<string, { label: string; bg: string; color: string }> = {
  low:      { label: '↓ Низкий',    bg: '#f3f4f6', color: '#6b7280' },
  normal:   { label: '→ Обычный',   bg: '#dbeafe', color: '#1d4ed8' },
  high:     { label: '↑ Высокий',   bg: '#ffedd5', color: '#c2410c' },
  critical: { label: '🔴 Критичный', bg: '#fee2e2', color: '#b91c1c' },
}

export function StatusBadge({ status, showDot = false }: { status: string; showDot?: boolean }) {
  const cfg = STATUS[status] ?? { label: status, bg: '#f3f4f6', color: '#6b7280', dot: '#9ca3af' }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 8px', borderRadius: 100, fontSize: 12, fontWeight: 500,
      background: cfg.bg, color: cfg.color,
    }}>
      {showDot && <span style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.dot, flexShrink: 0 }} />}
      {cfg.label}
    </span>
  )
}

export function PriorityBadge({ priority }: { priority: string }) {
  const cfg = PRIORITY[priority] ?? { label: priority, bg: '#f3f4f6', color: '#6b7280' }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '3px 8px', borderRadius: 100, fontSize: 12, fontWeight: 500,
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.label}
    </span>
  )
}

export const STATUS_DOT_COLOR: Record<string, string> = {
  new: '#3b82f6', open: '#6366f1', in_progress: '#f59e0b',
  waiting_for_user: '#f97316', resolved: '#22c55e', closed: '#9ca3af', duplicate: '#a855f7',
}
