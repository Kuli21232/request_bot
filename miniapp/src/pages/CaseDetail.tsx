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
import { Loader } from '../components/Loader'
import { getCasePriorityLabel, getCaseStatusLabel, getReadableSignalTitle, getRecommendedActionLabel, getSignalKindLabel } from '../utils/flow'

export default function CaseDetail() {
  const { id } = useParams()
  const [flowCase, setFlowCase] = useState<FlowCaseDetail | null>(null)
  const [viewer, setViewer] = useState<TeamProfile | null>(null)
  const [people, setPeople] = useState<TeamUser[]>([])
  const [selectedResponsible, setSelectedResponsible] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(flowCase.signals ?? []).map((signal) => (
              <Link key={signal.id} to={`/signals/${signal.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="soft-card" style={{ padding: '12px 13px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                    <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>{getSignalKindLabel(signal.kind)}</span>
                    {signal.store && <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>{signal.store}</span>}
                    {signal.submitter_id && (
                      <span className="pill" style={{ background: '#ecfeff', color: '#0f766e' }}>
                        {signal.submitter_name || 'Автор'}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.35 }}>
                    {getReadableSignalTitle(signal)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
