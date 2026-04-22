/* ─── Status → label / color map ─────────────────────────── */
const STATUS: Record<string, { label: string; bg: string; color: string; dot: string }> = {
  new:              { label: 'Новая',        bg: '#dbeafe', color: '#1e40af', dot: '#3b82f6' },
  open:             { label: 'Открыта',      bg: '#e0e7ff', color: '#3730a3', dot: '#6366f1' },
  in_progress:      { label: 'В работе',     bg: '#fef3c7', color: '#92400e', dot: '#f59e0b' },
  waiting_for_user: { label: 'Ждёт ответа',  bg: '#ffedd5', color: '#9a3412', dot: '#f97316' },
  resolved:         { label: 'Решена',       bg: '#dcfce7', color: '#15803d', dot: '#22c55e' },
  closed:           { label: 'Закрыта',      bg: '#f1f5f9', color: '#475569', dot: '#94a3b8' },
  duplicate:        { label: 'Дубликат',     bg: '#f3e8ff', color: '#7e22ce', dot: '#a855f7' },
  watching:         { label: 'Наблюдение',   bg: '#e0f2fe', color: '#075985', dot: '#0284c7' },
}

/* ─── Priority → label / color map ──────────────────────── */
const PRIORITY: Record<string, { label: string; bg: string; color: string; dot: string }> = {
  low:      { label: 'Низкий',    bg: '#f1f5f9', color: '#475569', dot: '#94a3b8' },
  normal:   { label: 'Обычный',   bg: '#dbeafe', color: '#1e40af', dot: '#3b82f6' },
  high:     { label: 'Высокий',   bg: '#ffedd5', color: '#9a3412', dot: '#f97316' },
  critical: { label: 'Критичный', bg: '#fee2e2', color: '#b91c1c', dot: '#ef4444' },
}

/* ─── Signal type → label / color ───────────────────────── */
const SIGNAL_KIND: Record<string, { label: string; bg: string; color: string }> = {
  problem:       { label: 'Проблема',    bg: '#fee2e2', color: '#b91c1c' },
  request:       { label: 'Запрос',      bg: '#dbeafe', color: '#1e40af' },
  status_update: { label: 'Статус',      bg: '#f1f5f9', color: '#334155' },
  photo_report:  { label: 'Фотоотчёт',  bg: '#fce7f3', color: '#9d174d' },
  delivery:      { label: 'Поставка',    bg: '#ecfdf5', color: '#15803d' },
  finance:       { label: 'Финансы',     bg: '#fef3c7', color: '#92400e' },
  compliance:    { label: 'ЕГАИС',       bg: '#f3e8ff', color: '#7e22ce' },
  inventory:     { label: 'Остатки',     bg: '#e0f2fe', color: '#075985' },
  'chat/noise':  { label: 'Переписка',   bg: '#f8fafc', color: '#64748b' },
  escalation:    { label: 'Эскалация',   bg: '#fff7ed', color: '#9a3412' },
  news:          { label: 'Новость',     bg: '#f0fdf4', color: '#166534' },
}

/* ─── Components ─────────────────────────────────────────── */

export function StatusBadge({ status, showDot = true }: { status: string; showDot?: boolean }) {
  const cfg = STATUS[status] ?? { label: status, bg: '#f1f5f9', color: '#475569', dot: '#94a3b8' }
  return (
    <span className="chip" style={{ background: cfg.bg, color: cfg.color }}>
      {showDot && (
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: cfg.dot, flexShrink: 0 }} />
      )}
      {cfg.label}
    </span>
  )
}

export function PriorityBadge({ priority }: { priority: string }) {
  const cfg = PRIORITY[priority] ?? { label: priority, bg: '#f1f5f9', color: '#475569', dot: '#94a3b8' }
  return (
    <span className="chip" style={{ background: cfg.bg, color: cfg.color }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: cfg.dot, flexShrink: 0 }} />
      {cfg.label}
    </span>
  )
}

export function SignalKindBadge({ kind }: { kind: string }) {
  const cfg = SIGNAL_KIND[kind] ?? { label: kind, bg: '#f1f5f9', color: '#334155' }
  return (
    <span className="chip" style={{ background: cfg.bg, color: cfg.color }}>
      {cfg.label}
    </span>
  )
}

export const STATUS_DOT_COLOR: Record<string, string> = {
  new: '#3b82f6', open: '#6366f1', in_progress: '#f59e0b',
  waiting_for_user: '#f97316', resolved: '#22c55e', closed: '#94a3b8',
  duplicate: '#a855f7', watching: '#0284c7',
}
