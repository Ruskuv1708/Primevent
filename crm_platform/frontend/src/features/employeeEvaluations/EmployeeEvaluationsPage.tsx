import { useEffect, useMemo, useState, type FormEvent } from 'react'
import axios from 'axios'
import { getWorkspaceParams } from '../../shared/workspace'
import { roleMatches } from '../../shared/roleLabels'
import { useAppLayoutContext } from '../../shared/appLayoutContext'

type EmployeeSummary = {
  id: string
  full_name: string
  email?: string | null
  role?: string
  evaluation_count: number
  total_score: number
  average_score: number | null
  rank?: number | null
}

type TeamStats = {
  team_total_score: number
  team_average_score: number | null
  evaluation_count: number
  employee_count: number
  evaluated_employee_count: number
  top_employee: EmployeeSummary | null
  rankings: EmployeeSummary[]
}

type EvaluationUser = {
  id: string
  full_name: string
  email?: string | null
  role?: string
}

type EmployeeEvaluation = {
  id: string
  employee_id: string
  evaluator_id: string
  title: string
  description?: string | null
  score: number
  period_label?: string | null
  comment?: string | null
  employee?: EvaluationUser | null
  evaluator?: EvaluationUser | null
  updated_at?: string | null
}

type EvaluationForm = {
  title: string
  description: string
  score: number
  period_label: string
  comment: string
}

const emptyForm = (): EvaluationForm => ({
  title: '',
  description: '',
  score: 8,
  period_label: '',
  comment: '',
})

const formatDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const scoreTone = (score: number) => {
  if (score >= 8) return 'is-high'
  if (score >= 5) return 'is-mid'
  return 'is-low'
}

function EmployeeEvaluationsPage() {
  const { currentUser } = useAppLayoutContext()
  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [evaluations, setEvaluations] = useState<EmployeeEvaluation[]>([])
  const [teamStats, setTeamStats] = useState<TeamStats | null>(null)
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<EvaluationForm>(() => emptyForm())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const canManage = useMemo(() => (
    roleMatches(currentUser?.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])
  ), [currentUser?.role])
  const selectedEmployee = employees.find(employee => employee.id === selectedEmployeeId) || null
  const averageScore = selectedEmployee?.average_score
  const token = localStorage.getItem('crm_token')

  const authConfig = () => ({
    headers: { Authorization: `Bearer ${token}` },
    params: getWorkspaceParams(currentUser),
  })

  const loadEmployees = async () => {
    if (!token || !currentUser) return
    const response = await axios.get<EmployeeSummary[]>('/employee-evaluations/employees', authConfig())
    const nextEmployees = Array.isArray(response.data) ? response.data : []
    setEmployees(nextEmployees)
    setSelectedEmployeeId(prev => prev || nextEmployees[0]?.id || '')
  }

  const loadTeamStats = async () => {
    if (!token || !currentUser || !canManage) return
    const response = await axios.get<TeamStats>('/employee-evaluations/stats', authConfig())
    setTeamStats(response.data)
  }

  const loadEvaluations = async (employeeId = selectedEmployeeId) => {
    if (!token || !currentUser) return
    const params = {
      ...(getWorkspaceParams(currentUser) || {}),
      ...(employeeId ? { employee_id: employeeId } : {}),
    }
    const response = await axios.get<EmployeeEvaluation[]>('/employee-evaluations', {
      headers: { Authorization: `Bearer ${token}` },
      params,
    })
    setEvaluations(Array.isArray(response.data) ? response.data : [])
  }

  const loadPage = async () => {
    if (!token || !currentUser) return
    setLoading(true)
    setError(null)
    try {
      await Promise.all([
        loadEmployees(),
        canManage ? loadTeamStats() : Promise.resolve(),
      ])
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось загрузить оценки сотрудников')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPage()
  }, [currentUser?.id, currentUser?.workspace_id])

  useEffect(() => {
    if (!selectedEmployeeId) {
      setEvaluations([])
      return
    }
    void loadEvaluations(selectedEmployeeId)
  }, [selectedEmployeeId])

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm())
  }

  const startEditing = (evaluation: EmployeeEvaluation) => {
    setEditingId(evaluation.id)
    setForm({
      title: evaluation.title,
      description: evaluation.description || '',
      score: evaluation.score,
      period_label: evaluation.period_label || '',
      comment: evaluation.comment || '',
    })
  }

  const submitEvaluation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || !selectedEmployeeId || !canManage) return
    setSaving(true)
    setError(null)
    setMessage(null)
    const payload = {
      employee_id: selectedEmployeeId,
      title: form.title.trim(),
      description: form.description.trim() || null,
      score: form.score,
      period_label: form.period_label.trim() || null,
      comment: form.comment.trim() || null,
    }
    try {
      if (editingId) {
        await axios.patch(`/employee-evaluations/${editingId}`, payload, authConfig())
      } else {
        await axios.post('/employee-evaluations', payload, authConfig())
      }
      setMessage(editingId ? 'KPI-пункт обновлен' : 'KPI-пункт добавлен')
      resetForm()
      await Promise.all([
        loadEmployees(),
        loadTeamStats(),
      ])
      await loadEvaluations(selectedEmployeeId)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось сохранить KPI-пункт')
    } finally {
      setSaving(false)
    }
  }

  const deleteEvaluation = async (evaluationId: string) => {
    if (!token || !canManage) return
    if (!window.confirm('Удалить этот KPI-пункт?')) return
    setSaving(true)
    setError(null)
    try {
      await axios.delete(`/employee-evaluations/${evaluationId}`, authConfig())
      if (editingId === evaluationId) resetForm()
      await Promise.all([
        loadEmployees(),
        loadTeamStats(),
      ])
      await loadEvaluations(selectedEmployeeId)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось удалить KPI-пункт')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="crm-page-shell employee-evaluations-page">
      <div className="page-head">
        <div className="page-head-left">
          <span className="page-greeting">KPI</span>
          <h1 className="page-h1">Оценка сотрудников</h1>
          <span className="page-sub">Индивидуальные пункты оценки сотрудников с баллами от 1 до 10.</span>
        </div>
      </div>

      {error && <p className="crm-form-message is-error">{error}</p>}
      {message && <p className="crm-form-message is-success">{message}</p>}

      {canManage && (
        <section className="section crm-section-panel employee-rating-panel">
          <div className="section-head">
            <div>
              <h2 className="section-title">Командный KPI</h2>
              <span className="section-sub">
                Общий балл команды и рейтинг сотрудников по качеству KPI.
              </span>
            </div>
          </div>

          <div className="employee-team-score-grid">
            <div className="employee-team-score-card">
              <span>Средний балл команды</span>
              <strong>{teamStats?.team_average_score ?? '—'}</strong>
              <small>/ 10</small>
            </div>
            <div className="employee-team-score-card">
              <span>Сумма баллов</span>
              <strong>{teamStats?.team_total_score ?? 0}</strong>
              <small>{teamStats?.evaluation_count ?? 0} KPI-пунктов</small>
            </div>
            <div className="employee-team-score-card">
              <span>Оценено сотрудников</span>
              <strong>{teamStats ? `${teamStats.evaluated_employee_count}/${teamStats.employee_count}` : '—'}</strong>
              <small>есть хотя бы один KPI</small>
            </div>
            <div className="employee-team-score-card">
              <span>Лидер</span>
              <strong>{teamStats?.top_employee?.full_name || '—'}</strong>
              <small>
                {teamStats?.top_employee?.average_score != null
                  ? `${teamStats.top_employee.average_score} средний балл`
                  : 'пока нет оценок'}
              </small>
            </div>
          </div>

          <div className="employee-ranking-list">
            {(teamStats?.rankings || []).map(employee => (
              <button
                type="button"
                key={employee.id}
                className={employee.id === selectedEmployeeId ? 'employee-ranking-row is-selected' : 'employee-ranking-row'}
                onClick={() => {
                  setSelectedEmployeeId(employee.id)
                  resetForm()
                }}
              >
                <span className="employee-ranking-place">
                  {employee.rank ? `#${employee.rank}` : '—'}
                </span>
                <span className="employee-ranking-person">
                  <strong>{employee.full_name}</strong>
                  <small>{employee.email || employee.role || 'Сотрудник'}</small>
                </span>
                <span className="employee-ranking-metric">
                  <strong>{employee.average_score ?? '—'}</strong>
                  <small>средний</small>
                </span>
                <span className="employee-ranking-metric">
                  <strong>{employee.total_score}</strong>
                  <small>сумма</small>
                </span>
                <span className="employee-ranking-metric">
                  <strong>{employee.evaluation_count}</strong>
                  <small>KPI</small>
                </span>
              </button>
            ))}
            {!loading && teamStats && teamStats.rankings.length === 0 && (
              <div className="employee-empty-state">Для рейтинга пока нет сотрудников.</div>
            )}
          </div>
        </section>
      )}

      <div className="employee-evaluation-layout">
        <section className="section crm-section-panel employee-list-panel">
          <div className="section-head">
            <div>
              <h2 className="section-title">Сотрудники</h2>
              <span className="section-sub">{loading ? 'Загрузка...' : `${employees.length} сотрудников`}</span>
            </div>
          </div>
          <div className="employee-list">
            {employees.map(employee => (
              <button
                type="button"
                key={employee.id}
                className={employee.id === selectedEmployeeId ? 'employee-card is-selected' : 'employee-card'}
                onClick={() => {
                  setSelectedEmployeeId(employee.id)
                  resetForm()
                }}
              >
                <span>
                  <strong>{employee.full_name}</strong>
                  <small>{employee.email || employee.role || 'Сотрудник'}</small>
                </span>
                <span className="employee-score-summary">
                  {employee.average_score ?? '—'}
                  <small>{employee.evaluation_count} KPI</small>
                </span>
              </button>
            ))}
            {!loading && employees.length === 0 && (
              <div className="employee-empty-state">Сотрудники не найдены.</div>
            )}
          </div>
        </section>

        <section className="section crm-section-panel employee-kpi-panel">
          <div className="section-head">
            <div>
              <h2 className="section-title">{selectedEmployee?.full_name || 'KPI-пункты'}</h2>
              <span className="section-sub">
                Средний балл: {averageScore ?? '—'} · {evaluations.length} пунктов
              </span>
            </div>
          </div>

          <div className="employee-kpi-list">
            {evaluations.map(evaluation => (
              <article key={evaluation.id} className="employee-kpi-item">
                <div className="employee-kpi-score">
                  <span className={`employee-score-badge ${scoreTone(evaluation.score)}`}>{evaluation.score}</span>
                  <small>/ 10</small>
                </div>
                <div className="employee-kpi-body">
                  <div className="employee-kpi-title-row">
                    <h3>{evaluation.title}</h3>
                    <span>{evaluation.period_label || 'Без периода'}</span>
                  </div>
                  {evaluation.description && <p>{evaluation.description}</p>}
                  {evaluation.comment && <strong>{evaluation.comment}</strong>}
                  <small>
                    Оценил: {evaluation.evaluator?.full_name || 'Администратор'} · Обновлено: {formatDate(evaluation.updated_at)}
                  </small>
                </div>
                {canManage && (
                  <div className="employee-kpi-actions">
                    <button type="button" className="btn btn--secondary btn--sm" onClick={() => startEditing(evaluation)}>
                      Изменить
                    </button>
                    <button type="button" className="btn btn--secondary btn--sm" disabled={saving} onClick={() => deleteEvaluation(evaluation.id)}>
                      Удалить
                    </button>
                  </div>
                )}
              </article>
            ))}
            {!loading && evaluations.length === 0 && (
              <div className="employee-empty-state">Для выбранного сотрудника KPI-пункты еще не добавлены.</div>
            )}
          </div>
        </section>

        <aside className="section crm-section-panel employee-evaluation-form-panel">
          {canManage ? (
            <form className="employee-evaluation-form" onSubmit={submitEvaluation}>
              <div className="section-head">
                <div>
                  <h2 className="section-title">{editingId ? 'Редактировать KPI' : 'Новый KPI-пункт'}</h2>
                  <span className="section-sub">{selectedEmployee?.full_name || 'Выберите сотрудника'}</span>
                </div>
              </div>

              <label>
                Название пункта
                <input
                  className="input"
                  value={form.title}
                  onChange={event => setForm(prev => ({ ...prev, title: event.target.value }))}
                  placeholder="Пунктуальность"
                  required
                />
              </label>
              <label>
                Описание
                <textarea
                  className="textarea"
                  value={form.description}
                  onChange={event => setForm(prev => ({ ...prev, description: event.target.value }))}
                  placeholder="Что именно оцениваем"
                />
              </label>
              <label>
                Период
                <input
                  className="input"
                  value={form.period_label}
                  onChange={event => setForm(prev => ({ ...prev, period_label: event.target.value }))}
                  placeholder="Июнь 2026"
                />
              </label>
              <label className="employee-score-field">
                Оценка
                <span className={`employee-score-badge ${scoreTone(form.score)}`}>{form.score}</span>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={form.score}
                  onChange={event => setForm(prev => ({ ...prev, score: Number(event.target.value) }))}
                />
              </label>
              <label>
                Комментарий администратора
                <textarea
                  className="textarea"
                  value={form.comment}
                  onChange={event => setForm(prev => ({ ...prev, comment: event.target.value }))}
                  placeholder="Короткий вывод по пункту"
                />
              </label>

              <div className="employee-form-actions">
                <button type="submit" className="btn btn--primary" disabled={saving || !selectedEmployeeId}>
                  {saving ? 'Сохранение...' : editingId ? 'Сохранить' : 'Добавить'}
                </button>
                {editingId && (
                  <button type="button" className="btn btn--secondary" onClick={resetForm}>
                    Новый
                  </button>
                )}
              </div>
            </form>
          ) : (
            <div className="employee-readonly-note">
              <h2 className="section-title">Просмотр оценок</h2>
              <p>Ваш аккаунт может смотреть свои KPI-оценки. Добавлять и редактировать пункты могут администраторы.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

export default EmployeeEvaluationsPage
