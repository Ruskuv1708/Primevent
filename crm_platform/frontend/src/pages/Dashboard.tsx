import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import theme from '../shared/theme'
import { normalizeRole, roleMatches } from '../shared/roleLabels'
import { getWorkspaceParams } from '../shared/workspace'
import type { FormField, FormTemplate } from '../features/forms/types'
import type { RequestItem } from '../features/requests/types'
import useIsMobile from '../shared/useIsMobile'
import { getPriorityColor } from '../features/requests/priority'
import {
  buildRequestTableModel,
  getNextSortState,
  sortRequestTableRows,
  type RequestTableSortState,
} from '../features/requests/requestTableModel'
import useRegistryAutocomplete, {
  isClientField,
  isCompanyField,
  isDepartmentField,
  isPriorityField,
  isStatusField,
  REQUEST_PRIORITY_OPTIONS,
  REQUEST_STATUS_OPTIONS,
} from '../shared/useRegistryAutocomplete'
import { useI18n } from '../shared/i18nContext'

const normalizeUserRole = (user: any) => ({
  ...user,
  role: normalizeRole(user.role),
})

const makeEmptyPayload = (fields: FormField[], defaultDepartmentId: string = '') => {
  const next: Record<string, any> = {}
  fields.forEach(field => {
    if (field.type === 'boolean') {
      next[field.key] = false
    } else if (isStatusField(field)) {
      next[field.key] = REQUEST_STATUS_OPTIONS[0].value
    } else if (isPriorityField(field)) {
      next[field.key] = 'medium'
    } else if (isDepartmentField(field)) {
      next[field.key] = defaultDepartmentId
    } else {
      next[field.key] = ''
    }
  })
  return next
}

function Dashboard() {
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [requests, setRequests] = useState<RequestItem[]>([])
  const [templates, setTemplates] = useState<FormTemplate[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [quickPayload, setQuickPayload] = useState<Record<string, any>>({})
  const [quickSubmitting, setQuickSubmitting] = useState(false)
  const [quickMessage, setQuickMessage] = useState<string | null>(null)
  const [quickError, setQuickError] = useState<string | null>(null)
  const [showQuickRequestModal, setShowQuickRequestModal] = useState(false)
  const [recentTableSort, setRecentTableSort] = useState<RequestTableSortState>({
    columnId: null,
    direction: null,
  })
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const { t } = useI18n()
  const { companyNames, clientNames } = useRegistryAutocomplete(currentUser)

  const canQuickCreate = useMemo(() => {
    return roleMatches(currentUser?.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN', 'MANAGER', 'USER'])
  }, [currentUser?.role])

  const selectedTemplate = useMemo(() => {
    if (!templates.length) return null
    if (!selectedTemplateId) return templates[0]
    return templates.find(t => t.id === selectedTemplateId) || templates[0]
  }, [templates, selectedTemplateId])

  const quickFields = useMemo<FormField[]>(() => selectedTemplate?.schema_structure || [], [selectedTemplate])
  const departmentNameMap = useMemo(() => {
    const map = new Map<string, string>()
    departments.forEach(dep => {
      if (!dep?.id || !dep?.name) return
      map.set(String(dep.id).toLowerCase(), String(dep.name))
    })
    return map
  }, [departments])
  const recentRequests = useMemo(() => {
    return [...requests]
      .sort((a, b) => {
        const aTime = new Date(a?.created_at || a?.updated_at || 0).getTime()
        const bTime = new Date(b?.created_at || b?.updated_at || 0).getTime()
        return bTime - aTime
      })
      .slice(0, 20)
  }, [requests])
  const requestTableModel = useMemo(() => {
    return buildRequestTableModel({
      requests: recentRequests,
      templates,
      resolveDepartmentName: departmentId => {
        if (!departmentId) return '—'
        return departmentNameMap.get(String(departmentId).toLowerCase()) || '—'
      },
      resolveAssignedName: request => {
        if (request.assignee?.full_name) return request.assignee.full_name
        return request.assigned_to_id || 'Unassigned'
      },
    })
  }, [recentRequests, templates, departmentNameMap])
  const sortedRecentRows = useMemo(() => {
    return sortRequestTableRows(requestTableModel.rows, recentTableSort)
  }, [requestTableModel.rows, recentTableSort])

  useEffect(() => {
    const token = localStorage.getItem('crm_token')
    if (!token) {
      navigate('/')
      return
    }

    axios.get('/access/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    .then(async res => {
      const normalized = normalizeUserRole(res.data)
      setCurrentUser(normalized)
      const params = getWorkspaceParams(normalized)
      const canLoadTemplates = roleMatches(normalized.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN', 'MANAGER', 'USER'])

      try {
        const [reqRes, templateRes, departmentRes] = await Promise.all([
          axios.get('/workflow/requests', {
            headers: { Authorization: `Bearer ${token}` },
            params,
          }),
          canLoadTemplates
            ? axios.get('/forms/templates', {
                headers: { Authorization: `Bearer ${token}` },
                params,
              })
            : Promise.resolve({ data: [] }),
          canLoadTemplates
            ? axios.get('/workflow/departments', {
                headers: { Authorization: `Bearer ${token}` },
                params,
              })
            : Promise.resolve({ data: [] }),
        ])
        setRequests(reqRes.data)
        const loadedTemplates: FormTemplate[] = Array.isArray(templateRes.data) ? templateRes.data : []
        setTemplates(loadedTemplates)
        setDepartments(Array.isArray(departmentRes.data) ? departmentRes.data : [])
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      } finally {
        setLoading(false)
      }
    })
    .catch(err => {
      console.error('Error fetching user:', err)
      localStorage.removeItem('crm_token')
      navigate('/')
    })
  }, [navigate])

  useEffect(() => {
    if (!selectedTemplate) {
      setQuickPayload({})
      return
    }
    setSelectedTemplateId(selectedTemplate.id)
    setQuickPayload(makeEmptyPayload(selectedTemplate.schema_structure || [], departments[0]?.id || ''))
    setQuickMessage(null)
    setQuickError(null)
  }, [selectedTemplate?.id, departments[0]?.id])

  const getStatusColor = (status: string) => {
    return theme.colors.status[status as keyof typeof theme.colors.status] || theme.colors.gray.light
  }

  const getStatusTextColor = (status: string) => {
    return theme.colors.statusText[status as keyof typeof theme.colors.statusText] || '#333'
  }

  useEffect(() => {
    if (!recentTableSort.columnId) return
    if (requestTableModel.columns.some(column => column.id === recentTableSort.columnId)) return
    setRecentTableSort({ columnId: null, direction: null })
  }, [requestTableModel.columns, recentTableSort.columnId])

  const handleRecentSortClick = (columnId: string) => {
    setRecentTableSort(prev => getNextSortState(requestTableModel.columns, prev, columnId))
  }

  const renderSortIndicator = (columnId: string) => {
    const isActive = recentTableSort.columnId === columnId && Boolean(recentTableSort.direction)
    const isAsc = isActive && recentTableSort.direction === 'asc'
    const isDesc = isActive && recentTableSort.direction === 'desc'
    return (
      <span style={{ display: 'inline-flex', flexDirection: 'column', marginLeft: 4, lineHeight: 0.85 }}>
        <span style={{ fontSize: 8, color: isAsc ? '#111' : '#9b9b9b' }}>▲</span>
        <span style={{ fontSize: 8, color: isDesc ? '#111' : '#9b9b9b' }}>▼</span>
      </span>
    )
  }

  const updateQuickValue = (field: FormField, value: any) => {
    setQuickPayload(prev => ({ ...prev, [field.key]: value }))
  }

  const validateQuickPayload = () => {
    for (const field of quickFields) {
      if (!field.required) continue
      const value = quickPayload[field.key]
      if (value === '' || value === null || typeof value === 'undefined') {
        return `${field.label} is required`
      }
    }
    return null
  }

  const buildSubmitData = () => {
    const data: Record<string, any> = {}
    quickFields.forEach(field => {
      const value = quickPayload[field.key]
      if (field.type === 'number') {
        if (value === '' || value === null || Number.isNaN(value)) {
          return
        }
        data[field.key] = Number(value)
        return
      }
      if (field.type === 'boolean') {
        data[field.key] = Boolean(value)
        return
      }
      if (isDepartmentField(field) && (value === '' || value === null || typeof value === 'undefined')) {
        if (departments[0]?.id) {
          data[field.key] = departments[0].id
        }
        return
      }
      if (value === '' && !field.required) {
        return
      }
      data[field.key] = value
    })
    return data
  }

  const refreshRequests = async () => {
    const token = localStorage.getItem('crm_token')
    if (!token || !currentUser) return
    const params = getWorkspaceParams(currentUser)
    const reqRes = await axios.get('/workflow/requests', {
      headers: { Authorization: `Bearer ${token}` },
      params,
    })
    setRequests(reqRes.data)
  }

  const submitQuickRequest = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTemplate || !currentUser) return

    const token = localStorage.getItem('crm_token')
    if (!token) {
      navigate('/')
      return
    }

    const validationError = validateQuickPayload()
    if (validationError) {
      setQuickError(validationError)
      setQuickMessage(null)
      return
    }

    setQuickSubmitting(true)
    setQuickError(null)
    setQuickMessage(null)

    try {
      await axios.post('/forms/submit', {
        template_id: selectedTemplate.id,
        data: buildSubmitData(),
      }, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams(currentUser),
      })

      setQuickMessage(t('dashboard.requestSubmitted'))
      setQuickPayload(makeEmptyPayload(quickFields, departments[0]?.id || ''))
      setShowQuickRequestModal(false)
      await refreshRequests()
    } catch (err: any) {
      console.error('Failed to submit request:', err)
      const detail = err?.response?.data?.detail
      setQuickError(typeof detail === 'string' ? detail : t('dashboard.submitFailed'))
    } finally {
      setQuickSubmitting(false)
    }
  }

  if (loading) return <div style={{ padding: '50px', textAlign: 'center' }}>Loading...</div>
  if (!currentUser) return <div style={{ padding: '50px', textAlign: 'center' }}>No user data</div>

  return (
    <div className="crm-page-shell" style={{ padding: theme.spacing.md, backgroundColor: theme.colors.gray.lighter, minHeight: '100vh' }}>
      <div style={{
        marginBottom: '10px',
        padding: '10px 12px',
        borderRadius: '10px',
        background: '#fff',
        boxShadow: theme.shadows.sm,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '10px',
        flexWrap: 'wrap',
      }}>
        <div style={{ fontSize: '13px', color: theme.colors.gray.text }}>
          {t('dashboard.openRequests')}: <strong style={{ color: '#1f2d3d' }}>{requests.length}</strong>
        </div>
        <div className="crm-header-actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/requests')}
            style={{
              background: '#1890ff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {t('dashboard.viewRequests')}
          </button>
          <button
            onClick={() => navigate('/departments')}
            style={{
              background: '#13c2c2',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            Departments
          </button>
          <button
            onClick={() => setShowQuickRequestModal(true)}
            style={{
              background: '#111',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {t('dashboard.newRequest')}
          </button>
        </div>
      </div>

      {showQuickRequestModal && (
        <div
          onClick={() => setShowQuickRequestModal(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.45)',
            zIndex: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: isMobile ? '8px' : '16px',
          }}
        >
          <div
            onClick={event => event.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '1120px',
              maxHeight: '90vh',
              overflow: 'auto',
              background: '#fff',
              borderRadius: '10px',
              padding: '12px',
              boxShadow: theme.shadows.md,
            }}
          >
            <div
              className={isMobile ? 'crm-mobile-stack' : ''}
              style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}
            >
              <h2 style={{ margin: 0, fontSize: '22px' }}>{t('dashboard.quickRequest')}</h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => navigate('/forms')}
                  style={{
                    background: 'transparent',
                    border: '1px solid #ccc',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    cursor: 'pointer',
                    width: isMobile ? '100%' : 'auto',
                  }}
                >
                  {t('dashboard.manageTemplates')}
                </button>
                <button
                  onClick={() => setShowQuickRequestModal(false)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #ccc',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    cursor: 'pointer',
                    width: isMobile ? '100%' : 'auto',
                  }}
                >
                  {t('dashboard.close')}
                </button>
              </div>
            </div>

            {!canQuickCreate ? (
              <p style={{ color: theme.colors.gray.text, margin: 0 }}>{t('dashboard.cannotCreate')}</p>
            ) : templates.length === 0 ? (
              <p style={{ color: theme.colors.gray.text, margin: 0 }}>{t('dashboard.noTemplates')}</p>
            ) : (
              <form onSubmit={submitQuickRequest} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: theme.colors.gray.text }}>Template</label>
                  <select
                    value={selectedTemplate?.id || ''}
                    onChange={e => setSelectedTemplateId(e.target.value)}
                    style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                  >
                    {templates.map(template => (
                      <option key={template.id} value={template.id}>{template.name}</option>
                    ))}
                  </select>
                </div>

                {companyNames.length > 0 && (
                  <datalist id="dashboard-registry-company-options">
                    {companyNames.map(name => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                )}
                {clientNames.length > 0 && (
                  <datalist id="dashboard-registry-client-options">
                    {clientNames.map(name => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
                  {quickFields.map(field => (
                    <div key={field.key}>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: theme.colors.gray.text }}>
                        {field.label}{field.required ? ' *' : ''}
                      </label>
                      {field.type === 'boolean' ? (
                        <label style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input
                            type="checkbox"
                            checked={Boolean(quickPayload[field.key])}
                            onChange={e => updateQuickValue(field, e.target.checked)}
                          />
                          <span style={{ fontSize: '13px', color: theme.colors.gray.text }}>Yes / No</span>
                        </label>
                      ) : isStatusField(field) ? (
                        <select
                          value={quickPayload[field.key] || REQUEST_STATUS_OPTIONS[0].value}
                          onChange={e => updateQuickValue(field, e.target.value)}
                          style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                        >
                          {REQUEST_STATUS_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      ) : isPriorityField(field) ? (
                        <select
                          value={quickPayload[field.key] || 'medium'}
                          onChange={e => updateQuickValue(field, e.target.value)}
                          style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                        >
                          {REQUEST_PRIORITY_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      ) : isDepartmentField(field) ? (
                        <select
                          value={quickPayload[field.key] || (departments[0]?.id || '')}
                          onChange={e => updateQuickValue(field, e.target.value)}
                          style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                        >
                          {departments.length === 0 && <option value="">No departments</option>}
                          {departments.map(dep => (
                            <option key={dep.id} value={dep.id}>{dep.name}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
                          value={quickPayload[field.key] ?? ''}
                          onChange={e => updateQuickValue(field, e.target.value)}
                          list={
                            isCompanyField(field)
                              ? 'dashboard-registry-company-options'
                              : isClientField(field)
                                ? 'dashboard-registry-client-options'
                                : undefined
                          }
                          style={{ width: '100%', marginTop: '4px', padding: '8px 10px', borderRadius: '6px', border: '1px solid #ddd' }}
                        />
                      )}
                    </div>
                  ))}
                </div>

                {quickError && (
                  <div style={{ color: '#cf1322', fontSize: '13px' }}>{quickError}</div>
                )}
                {quickMessage && (
                  <div style={{ color: '#237804', fontSize: '13px' }}>{quickMessage}</div>
                )}

                <div>
                  <button
                    type="submit"
                    disabled={quickSubmitting}
                    style={{
                      background: quickSubmitting ? '#9cc4ff' : '#1890ff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '8px 14px',
                      cursor: quickSubmitting ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {quickSubmitting ? 'Submitting...' : 'Submit Request'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      <div style={{ background: 'white', borderRadius: '10px', padding: '14px', boxShadow: theme.shadows.md }}>
        <div className={isMobile ? 'crm-mobile-stack' : ''} style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '24px' }}>Recent Requests ({recentRequests.length})</h2>
          <button
            onClick={() => navigate('/requests')}
            style={{
              background: 'transparent',
              border: '1px solid #ccc',
              borderRadius: '6px',
              padding: '6px 10px',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            Full list
          </button>
        </div>
        {sortedRecentRows.length === 0 ? (
          <p style={{ color: theme.colors.gray.text, margin: 0 }}>No requests yet.</p>
        ) : (
          <div className="crm-inline-grid-scroll" style={{ border: '1px solid #000', borderRadius: '8px', overflow: 'auto' }}>
            <table
              style={{
                width: '100%',
                minWidth: `${Math.max(980, requestTableModel.columns.length * 140)}px`,
                borderCollapse: 'collapse',
              }}
            >
              <thead>
                <tr style={{ background: '#fafafa', textAlign: 'left' }}>
                  {requestTableModel.columns.map(column => (
                    <th key={column.id} style={recentTableHeaderCell}>
                      <button
                        type="button"
                        onClick={() => handleRecentSortClick(column.id)}
                        style={recentTableSortButton}
                      >
                        {column.label}
                        {renderSortIndicator(column.id)}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedRecentRows.map(row => {
                  const req = row.request
                  return (
                    <tr
                      key={req.id}
                      onClick={() => navigate(`/requests/${req.id}`)}
                      style={{ cursor: 'pointer' }}
                    >
                      {requestTableModel.columns.map(column => {
                        if (column.id === 'date') {
                          return <td key={column.id} style={recentTableBodyCell}>{row.dateText}</td>
                        }
                        if (column.id === 'template') {
                          return <td key={column.id} style={recentTableBodyCell}>{row.templateName}</td>
                        }
                        if (column.id === 'uptime') {
                          return <td key={column.id} style={recentTableBodyCell}>{row.openForText}</td>
                        }
                        if (column.id === 'status') {
                          return (
                            <td key={column.id} style={recentTableBodyCell}>
                              <span style={{
                                display: 'inline-block',
                                background: getStatusColor(req.status),
                                color: getStatusTextColor(req.status),
                                padding: '4px 8px',
                                borderRadius: '999px',
                                fontSize: '11px',
                                lineHeight: 1,
                              }}>
                                {row.statusText}
                              </span>
                            </td>
                          )
                        }
                        if (column.id === 'priority') {
                          return (
                            <td key={column.id} style={recentTableBodyCell}>
                              <span style={{
                                display: 'inline-block',
                                background: getPriorityColor(row.priority),
                                color: '#fff',
                                padding: '4px 8px',
                                borderRadius: '999px',
                                fontSize: '11px',
                                lineHeight: 1,
                                textTransform: 'uppercase',
                              }}>
                                {row.priority}
                              </span>
                            </td>
                          )
                        }
                        if (column.id === 'department') {
                          return <td key={column.id} style={recentTableBodyCell}>{row.departmentName}</td>
                        }
                        if (column.id === 'assigned_to') {
                          return <td key={column.id} style={recentTableBodyCell}>{row.assignedName}</td>
                        }
                        return (
                          <td key={column.id} style={recentTableBodyCell}>
                            <span title={row.dynamicValues[column.id] || '—'}>
                              {row.dynamicValues[column.id] || '—'}
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

const recentTableHeaderCell = {
  borderBottom: '1px solid #000',
  borderRight: '1px solid #000',
  padding: '8px 10px',
  fontSize: '12px',
  fontWeight: 700,
  color: '#555',
}

const recentTableSortButton = {
  background: 'transparent',
  border: 'none',
  padding: 0,
  margin: 0,
  font: 'inherit',
  color: 'inherit',
  cursor: 'pointer',
  width: '100%',
  display: 'inline-flex',
  alignItems: 'center',
  textAlign: 'left' as const,
  whiteSpace: 'nowrap' as const,
}

const recentTableBodyCell = {
  borderBottom: '1px solid #000',
  borderRight: '1px solid #000',
  padding: '8px 10px',
  fontSize: '12px',
  color: '#555',
  whiteSpace: 'nowrap' as const,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  maxWidth: '240px',
}

export default Dashboard
