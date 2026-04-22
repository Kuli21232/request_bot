import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  assignCaseResponsible,
  getCase,
  getMyProfile,
  getTeamUsers,
  type FlowCaseDetail,
  type TeamProfile,
  type TeamUser,
} from '../api/client'
import { AuthorAvatar } from '../components/AuthorAvatar'
import { Loader } from '../components/Loader'
import { getCasePriorityLabel, getCaseStatusLabel, getReadableSignalTitle, getRecommendedActionLabel, getSignalKindHint, getSignalKindLabel } from '../utils/flow'

function timeAgo(iso?: string) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч`
  return `${Math.floor(hrs / 24)} д`
}

export default function CaseDetail() {
  const { id } = useParams()
  const [flowCase, setFlowCase] = useState<FlowCaseDetail | null>(null)
  const [viewer, setViewer] = useState<TeamProfile | null>(null)
  const [people, setPeople] = useState<TeamUser[]>([])
  const [selectedResponsible, setSelectedResponsible] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [accessDenied, setAccessDenied] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    setAccessDenied(false)
    try {
      const [caseData, profileData] = await Promise.all([
        getCase(Number(id)),
        getMyProfile(),
      ])
      setFlowCase(caseData)
      setViewer(profileData)
      setSelectedResponsible(caseData.responsible_user_id ? String(caseData.responsible_user_id) : '')

      if (profileData.permissions.can_assign_responsible) {
        const users = await getTeamUsers()
        setPeople(users)
      }
    } catch (err: any) {
      if (err?.response?.status === 403) setAccessDenied(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const saveResponsible = async () => {
    if (!flowCase) return
    setSaving(true)
    try {
      await assignCaseResponsible(flowCase.id, selectedResponsible ? Number(selectedResponsible) : null)
      await load()
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div style={{ padding: '40px 0' }}><Loader /></div>
  if (accessDenied) return <div style={{ padding: 20, color: 'var(--text-soft)' }}>Нет доступа к этой ситуации</div>
  if (!flowCase) return <div style={{ padding: 20, color: 'var(--text-soft)' }}>Ситуация не найдена</div>

  return (
    <div className="app-shell">
      <div className="screen-section" style={{ marginTop: 12 }}>
        <div
          className="glass-card"
          style={{
            padding: '18px 16px',
            background: 'linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%)',
            color: '#fff',
          }}
        >
          <div style={{ fontSize: 22, fontWeight: 800, lineHeight: 1.25 }}>{flowCase.title}</div>
          {flowCase.summary && <div style={{ marginTop: 9, fontSize: 14, opacity: 0.9, lineHeight: 1.45 }}>{flowCase.summary}</div>}
          <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{getCaseStatusLabel(flowCase.status)}</span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{getCasePriorityLabel(flowCase.priority)}</span>
            <span className="pill" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{flowCase.signal_count} сообщений</span>
          </div>
        </div>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 10 }}>Кто отвечает за ситуацию</div>
          <div style={{ display: 'grid', gap: 10 }}>
            <div className="soft-card" style={{ padding: '13px 13px 12px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 6 }}>Текущий ответственный</div>
              {flowCase.responsible_user_id ? (
                <Link to={`/team/${flowCase.responsible_user_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)' }}>
                    {flowCase.responsible_user_name || 'Сотрудник'}
                  </div>
                  {flowCase.assigned_at && (
                    <div style={{ fontSize: 12, color: 'var(--text-soft)', marginTop: 4 }}>
                      Назначен: {new Date(flowCase.assigned_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </Link>
              ) : (
                <div style={{ fontSize: 14, color: 'var(--text-soft)' }}>Пока не назначен</div>
              )}
            </div>
            {flowCase.suggested_owner_id && (
              <div className="soft-card" style={{ padding: '13px 13px 12px' }}>
                <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 6 }}>Кого предлагает AI</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>
                  {flowCase.suggested_owner_name}
                </div>
              </div>
            )}
            {viewer?.permissions.can_assign_responsible && (
              <div className="soft-card" style={{ padding: '13px 13px 12px' }}>
                <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 8 }}>Назначить ответственного</div>
                <select
                  value={selectedResponsible}
                  onChange={(event) => setSelectedResponsible(event.target.value)}
                  style={{
                    width: '100%',
                    borderRadius: 14,
                    border: '1px solid rgba(148,163,184,0.22)',
                    background: '#fff',
                    padding: '12px 14px',
                    fontSize: 14,
                    outline: 'none',
                  }}
                >
                  <option value="">Не назначать</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {[person.first_name, person.last_name].filter(Boolean).join(' ')}{person.username ? ` (@${person.username})` : ''}
                    </option>
                  ))}
                </select>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
                  <button
                    type="button"
                    onClick={saveResponsible}
                    disabled={saving}
                    className="filter-chip active"
                    style={{ opacity: saving ? 0.65 : 1 }}
                  >
                    Сохранить
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 8 }}>Что требует внимания</div>
          <div style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-main)' }}>
            {getRecommendedActionLabel(flowCase.recommended_action) || 'Пока ситуация собрана для наблюдения, без обязательного действия.'}
          </div>
        </section>
      </div>

      <div className="screen-section">
        <section className="glass-card" style={{ padding: 16 }}>
          <div className="section-title" style={{ fontSize: 17, marginBottom: 10 }}>Какие сообщения вошли</div>
          {(flowCase.signals ?? []).length === 0 ? (
            <div style={{ fontSize: 13, color: 'var(--text-soft)', padding: '6px 0' }}>
              Сообщений пока нет.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {(flowCase.signals ?? []).map((signal) => (
                <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="soft-card" style={{ padding: '12px 13px' }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 8 }}>
                      <AuthorAvatar name={signal.submitter_name} userId={signal.submitter_id} size={30} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                          <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-main)' }}>
                            {signal.submitter_name || 'Автор не определён'}
                          </span>
                          {signal.submitter_username && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>@{signal.submitter_username}</span>
                          )}
                          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                            {timeAgo(signal.happened_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-main)', lineHeight: 1.45, whiteSpace: 'pre-wrap' }}>
                      {getReadableSignalTitle(signal)}
                    </div>
                    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 8 }}>
                      <span className="chip" style={{ background: '#eff6ff', color: '#1d4ed8' }} title={getSignalKindHint(signal.kind)}>
                        {getSignalKindLabel(signal.kind)}
                      </span>
                      {signal.store && <span className="chip pill-neutral">{signal.store}</span>}
                      {signal.requires_attention && (
                        <span className="chip" style={{ background: '#fee2e2', color: '#b91c1c' }}>⚠ Внимание</span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
