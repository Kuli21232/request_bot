import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getRequest, addComment, updateStatus, updatePriority,
  assignRequest, rateRequest, getAgents
} from '../api/client'
import type { RequestDetail as ReqDetail, Comment, HistoryItem, Agent } from '../api/client'
import { StatusBadge, PriorityBadge } from '../components/StatusBadge'
import { Loader } from '../components/Loader'
import WebApp, { haptic } from '../telegram'

const STATUSES = [
  { value: 'new',             label: 'Новая',    color: '#3b82f6' },
  { value: 'open',            label: 'Открыта',  color: '#6366f1' },
  { value: 'in_progress',     label: 'В работе', color: '#f59e0b' },
  { value: 'waiting_for_user',label: 'Ожидание', color: '#f97316' },
  { value: 'resolved',        label: 'Решена',   color: '#22c55e' },
  { value: 'closed',          label: 'Закрыта',  color: '#9ca3af' },
]

const PRIORITIES = [
  { value: 'low',      label: '↓ Низкий',    color: '#6b7280' },
  { value: 'normal',   label: '→ Обычный',   color: '#3b82f6' },
  { value: 'high',     label: '↑ Высокий',   color: '#f97316' },
  { value: 'critical', label: '🔴 Критичный', color: '#ef4444' },
]

const ACTION_LABELS: Record<string, string> = {
  status_change: 'Смена статуса',
  priority_change: 'Смена приоритета',
  assignment: 'Назначение',
}

export default function RequestDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [req, setReq] = useState<ReqDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'info' | 'chat' | 'history'>('info')
  const [comment, setComment] = useState('')
  const [isInternal, setIsInternal] = useState(false)
  const [sending, setSending] = useState(false)
  const [rating, setRating] = useState(0)
  const [agents, setAgents] = useState<Agent[]>([])
  const [showAssign, setShowAssign] = useState(false)
  const [showPriority, setShowPriority] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const load = async () => {
    try {
      const data = await getRequest(Number(id))
      setReq(data)
      if (data.satisfaction_score) setRating(data.satisfaction_score)
    } catch {
      WebApp.showAlert('Заявка не найдена')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  useEffect(() => {
    if (tab === 'chat') chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [tab, req?.comments])

  const isAgent = ['agent', 'supervisor', 'admin'].includes(req?.current_user_role ?? '')

  const handleStatus = async (status: string) => {
    if (!req || req.status === status) return
    haptic.medium()
    try {
      await updateStatus(req.id, status)
      haptic.success()
      load()
    } catch { haptic.error(); WebApp.showAlert('Ошибка смены статуса') }
  }

  const handlePriority = async (priority: string) => {
    if (!req) return
    haptic.medium()
    try {
      await updatePriority(req.id, priority)
      haptic.success()
      setShowPriority(false)
      load()
    } catch { haptic.error() }
  }

  const handleAssign = async (agentId: number) => {
    if (!req) return
    haptic.medium()
    try {
      await assignRequest(req.id, agentId)
      haptic.success()
      setShowAssign(false)
      load()
    } catch { haptic.error() }
  }

  const handleComment = async () => {
    if (!comment.trim() || !req) return
    setSending(true)
    haptic.light()
    try {
      await addComment(req.id, comment.trim(), isInternal)
      setComment('')
      haptic.success()
      load()
    } catch { haptic.error(); WebApp.showAlert('Ошибка отправки') }
    finally { setSending(false) }
  }

  const handleRate = async (score: number) => {
    if (!req) return
    setRating(score)
    haptic.medium()
    try {
      await rateRequest(req.id, score)
      haptic.success()
      WebApp.showAlert('Спасибо за оценку!')
      load()
    } catch { haptic.error() }
  }

  const loadAgents = async () => {
    if (agents.length > 0) { setShowAssign(true); return }
    try {
      const list = await getAgents()
      setAgents(list)
      setShowAssign(true)
    } catch { WebApp.showAlert('Не удалось загрузить агентов') }
  }

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '70vh' }}><Loader /></div>
  if (!req) return <div style={{ padding: 20, color: '#ef4444' }}>Заявка не найдена</div>

  const slaDate = req.sla_deadline ? new Date(req.sla_deadline) : null
  const canRate = req.status === 'resolved' && !req.satisfaction_score

  return (
    <div style={{ paddingBottom: 120, minHeight: '100vh' }}>
      {/* Back button + header */}
      <div style={{
        background: req.sla_breached
          ? 'linear-gradient(135deg, #dc2626, #ef4444)'
          : 'linear-gradient(135deg, #1a56db, #2481cc)',
        padding: '12px 16px 16px',
      }}>
        <button onClick={() => navigate(-1)} style={{
          background: 'rgba(255,255,255,0.2)', border: 'none', borderRadius: 100,
          color: '#fff', fontSize: 13, padding: '5px 12px', cursor: 'pointer', marginBottom: 8,
        }}>
          ← Назад
        </button>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)', marginBottom: 4 }}>
              {req.ticket_number}
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: '#fff', lineHeight: 1.3 }}>
              {req.subject || req.ai_subject || 'Без темы'}
            </div>
          </div>
          {req.sla_breached && <span style={{ fontSize: 20 }}>⚠️</span>}
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
          <StatusBadge status={req.status} showDot />
          <PriorityBadge priority={req.priority} />
          {req.department_name && (
            <span style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', fontSize: 12, padding: '3px 8px', borderRadius: 100 }}>
              {req.department_name}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(0,0,0,0.08)', background: 'var(--tg-theme-bg-color, #fff)', position: 'sticky', top: 0, zIndex: 10 }}>
        {(['info', 'chat', 'history'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: '12px 0', border: 'none', background: 'transparent', cursor: 'pointer',
            fontSize: 13, fontWeight: tab === t ? 600 : 400,
            color: tab === t ? '#2481cc' : '#999',
            borderBottom: tab === t ? '2px solid #2481cc' : '2px solid transparent',
          }}>
            {t === 'info' ? '📄 Описание' : t === 'chat' ? `💬 Чат (${req.comments?.length ?? 0})` : '🕐 История'}
          </button>
        ))}
      </div>

      {/* TAB: Info */}
      {tab === 'info' && (
        <div style={{ padding: '16px 14px' }}>
          {/* Meta info */}
          <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 14, padding: '14px', marginBottom: 12 }}>
            {[
              { label: 'Создана', value: new Date(req.created_at).toLocaleString('ru-RU') },
              slaDate && { label: 'SLA', value: slaDate.toLocaleString('ru-RU'), warn: req.sla_breached },
              req.assigned_to_name && { label: 'Исполнитель', value: req.assigned_to_name },
              req.first_response_at && { label: '1-й ответ', value: new Date(req.first_response_at).toLocaleString('ru-RU') },
              req.resolved_at && { label: 'Решена', value: new Date(req.resolved_at).toLocaleString('ru-RU') },
            ].filter(Boolean).map((row: any) => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                <span style={{ fontSize: 12, color: '#999' }}>{row.label}</span>
                <span style={{ fontSize: 12, fontWeight: 500, color: row.warn ? '#ef4444' : 'inherit' }}>{row.value}</span>
              </div>
            ))}
          </div>

          {/* Body */}
          <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 14, padding: 14, marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: '#999', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Текст заявки</div>
            <div style={{ fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{req.body}</div>
          </div>

          {/* AI analysis */}
          {(req.ai_category || req.ai_sentiment) && (
            <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 14, padding: 14, marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#0369a1', fontWeight: 600, marginBottom: 8 }}>🤖 AI-анализ</div>
              {req.ai_category && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <span style={{ color: '#666' }}>Категория</span>
                  <span style={{ fontWeight: 500, color: '#0369a1' }}>{req.ai_category}</span>
                </div>
              )}
              {req.ai_sentiment && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: '#666' }}>Тональность</span>
                  <span style={{ fontWeight: 500, color: '#0369a1' }}>
                    {req.ai_sentiment === 'positive' ? '😊 Позитивная' : req.ai_sentiment === 'negative' ? '😞 Негативная' : '😐 Нейтральная'}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Agent actions */}
          {isAgent && (
            <div style={{ background: 'var(--tg-theme-secondary-bg-color, #f5f5f5)', borderRadius: 14, padding: 14, marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#999', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>Управление</div>

              {/* Status */}
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>Статус</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {STATUSES.map(s => (
                    <button key={s.value} onClick={() => handleStatus(s.value)} style={{
                      padding: '6px 12px', borderRadius: 100, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500,
                      background: req.status === s.value ? s.color : 'rgba(0,0,0,0.06)',
                      color: req.status === s.value ? '#fff' : '#555',
                      opacity: req.status === s.value ? 1 : 0.8,
                    }}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Priority & Assign row */}
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => setShowPriority(!showPriority)} style={{
                  flex: 1, padding: '8px', borderRadius: 10, border: '1.5px solid rgba(0,0,0,0.1)',
                  background: '#fff', fontSize: 13, cursor: 'pointer',
                }}>
                  Приоритет ▾
                </button>
                <button onClick={loadAgents} style={{
                  flex: 1, padding: '8px', borderRadius: 10, border: '1.5px solid rgba(0,0,0,0.1)',
                  background: '#fff', fontSize: 13, cursor: 'pointer',
                }}>
                  Назначить ▾
                </button>
              </div>

              {showPriority && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {PRIORITIES.map(p => (
                    <button key={p.value} onClick={() => handlePriority(p.value)} style={{
                      padding: '6px 12px', borderRadius: 100, border: 'none', cursor: 'pointer', fontSize: 12,
                      background: req.priority === p.value ? p.color : 'rgba(0,0,0,0.06)',
                      color: req.priority === p.value ? '#fff' : '#555',
                    }}>
                      {p.label}
                    </button>
                  ))}
                </div>
              )}

              {showAssign && agents.length > 0 && (
                <div style={{ marginTop: 8, background: '#fff', borderRadius: 10, border: '1px solid rgba(0,0,0,0.1)', overflow: 'hidden' }}>
                  {agents.map(a => (
                    <button key={a.id} onClick={() => handleAssign(a.id)} style={{
                      width: '100%', padding: '10px 14px', border: 'none', background: 'transparent',
                      textAlign: 'left', cursor: 'pointer', fontSize: 14,
                      borderBottom: '1px solid rgba(0,0,0,0.05)',
                      color: req.assigned_to_id === a.id ? '#2481cc' : 'inherit',
                    }}>
                      {req.assigned_to_id === a.id ? '✓ ' : ''}{a.first_name}
                      {a.username && <span style={{ color: '#999', fontSize: 12 }}> @{a.username}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Rating for user */}
          {canRate && (
            <div style={{ background: '#fef3c7', borderRadius: 14, padding: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>⭐ Оцените решение</div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                {[1, 2, 3, 4, 5].map(score => (
                  <button key={score} onClick={() => handleRate(score)} style={{
                    background: 'none', border: 'none', cursor: 'pointer', fontSize: 32,
                    opacity: rating >= score ? 1 : 0.25,
                    transform: `scale(${rating === score ? 1.2 : 1})`,
                    transition: 'all 0.15s',
                  }}>⭐</button>
                ))}
              </div>
            </div>
          )}
          {req.satisfaction_score && (
            <div style={{ textAlign: 'center', padding: '12px 0', fontSize: 13, color: '#999' }}>
              Ваша оценка: {'⭐'.repeat(req.satisfaction_score)}
            </div>
          )}
        </div>
      )}

      {/* TAB: Chat */}
      {tab === 'chat' && (
        <div style={{ padding: '12px 14px' }}>
          {req.comments?.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999', fontSize: 14 }}>
              💬 Комментариев пока нет
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {req.comments?.map((c: Comment) => (
              <div key={c.id} style={{
                display: 'flex', flexDirection: 'column',
                alignItems: c.is_system ? 'center' : 'flex-start',
              }}>
                {c.is_system ? (
                  <div style={{ fontSize: 11, color: '#999', background: 'rgba(0,0,0,0.04)', borderRadius: 100, padding: '4px 12px' }}>
                    {c.body}
                  </div>
                ) : (
                  <div style={{ maxWidth: '85%' }}>
                    <div style={{ fontSize: 11, color: '#999', marginBottom: 3, marginLeft: 12 }}>
                      {c.author ?? 'Агент'} · {new Date(c.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      {c.is_internal && <span style={{ color: '#f59e0b', marginLeft: 4 }}>🔒 Внутренний</span>}
                    </div>
                    <div className={c.is_internal ? 'bubble-internal' : 'bubble-agent'} style={{ padding: '10px 14px', fontSize: 14, lineHeight: 1.5 }}>
                      {c.body}
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>
        </div>
      )}

      {/* TAB: History */}
      {tab === 'history' && (
        <div style={{ padding: '12px 14px' }}>
          {(!req.history || req.history.length === 0) ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>Нет истории</div>
          ) : (
            <div style={{ position: 'relative', paddingLeft: 24 }}>
              <div style={{ position: 'absolute', left: 7, top: 0, bottom: 0, width: 2, background: 'rgba(0,0,0,0.08)' }} />
              {req.history.map((h: HistoryItem, i: number) => (
                <div key={i} style={{ position: 'relative', marginBottom: 16 }}>
                  <div style={{ position: 'absolute', left: -20, top: 2, width: 10, height: 10, borderRadius: '50%', background: '#2481cc', border: '2px solid #fff' }} />
                  <div style={{ fontSize: 12, color: '#999' }}>{new Date(h.created_at).toLocaleString('ru-RU')}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, marginTop: 2 }}>
                    {ACTION_LABELS[h.action] ?? h.action}
                  </div>
                  {h.old_value && h.new_value && (
                    <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                      <span style={{ textDecoration: 'line-through', color: '#ef4444' }}>{h.old_value}</span>
                      {' → '}
                      <span style={{ color: '#22c55e', fontWeight: 500 }}>{h.new_value}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Fixed comment input */}
      {(tab === 'chat') && (
        <div style={{
          position: 'fixed', bottom: 60, left: 0, right: 0, padding: '10px 12px',
          background: 'var(--tg-theme-bg-color, #fff)', borderTop: '1px solid rgba(0,0,0,0.08)',
          boxShadow: '0 -2px 12px rgba(0,0,0,0.06)',
        }}>
          {isAgent && (
            <button onClick={() => setIsInternal(!isInternal)} style={{
              marginBottom: 6, padding: '3px 10px', borderRadius: 100, border: 'none', cursor: 'pointer',
              background: isInternal ? '#fef3c7' : 'rgba(0,0,0,0.06)',
              color: isInternal ? '#92400e' : '#999', fontSize: 11,
            }}>
              {isInternal ? '🔒 Внутренний комментарий' : '💬 Публичный ответ'}
            </button>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder={isInternal ? 'Внутренняя заметка...' : 'Написать комментарий...'}
              rows={2}
              style={{
                flex: 1, padding: '10px 12px', borderRadius: 14, border: '1.5px solid rgba(0,0,0,0.1)',
                fontSize: 14, outline: 'none', resize: 'none',
                background: isInternal ? '#fef3c7' : 'var(--tg-theme-secondary-bg-color, #f5f5f5)',
                color: 'var(--tg-theme-text-color, #000)',
              }}
            />
            <button
              onClick={handleComment}
              disabled={sending || !comment.trim()}
              style={{
                width: 44, borderRadius: 14, border: 'none', cursor: 'pointer',
                background: comment.trim() ? '#2481cc' : 'rgba(0,0,0,0.1)',
                color: '#fff', fontSize: 18, alignSelf: 'flex-end',
                opacity: sending ? 0.6 : 1,
              }}
            >
              {sending ? '…' : '↑'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
