import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import theme from '../../shared/theme'
import useIsMobile from '../../shared/useIsMobile'
import {
  getWorkspaceModuleSettings,
  type ModuleDefinition,
} from '../../shared/modules'
import { useI18n } from '../../shared/i18nContext'
import { LANGUAGE_OPTIONS, normalizeLanguage, type AppLanguage } from '../../shared/language'

// Define the shape of the form data
interface WorkspaceFormData {
  workspace_name: string;      
  subdomain_prefix: string; 
  admin_email: string;
  admin_password: string;
  admin_full_name: string;
  admin_language: AppLanguage;
}

interface AiSettings {
  provider: string;
  model: string;
  base_url: string;
  api_key_configured: boolean;
  api_key_preview: string | null;
}

interface WorkspaceUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
  language?: AppLanguage;
  is_active: boolean;
  workspace_id: string | null;
}

function WorkspaceManagementPage() {
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [workspaces, setWorkspaces] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // --- NEW STATE FOR CREATION ---
  const [showModal, setShowModal] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [moduleDefinitions, setModuleDefinitions] = useState<ModuleDefinition[]>([])
  const [moduleModalWorkspace, setModuleModalWorkspace] = useState<any | null>(null)
  const [moduleDraftEnabled, setModuleDraftEnabled] = useState<string[]>([])
  const [moduleSaving, setModuleSaving] = useState(false)
  const [aiSettings, setAiSettings] = useState<AiSettings | null>(null)
  const [aiDraft, setAiDraft] = useState({
    provider: 'deterministic',
    model: '',
    base_url: '',
    api_key: '',
  })
  const [aiSaving, setAiSaving] = useState(false)
  const [aiMessage, setAiMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [selectedPasswordWorkspaceId, setSelectedPasswordWorkspaceId] = useState('')
  const [workspaceUsers, setWorkspaceUsers] = useState<WorkspaceUser[]>([])
  const [workspaceUsersLoading, setWorkspaceUsersLoading] = useState(false)
  const [userPasswordDraft, setUserPasswordDraft] = useState({
    user_id: '',
    new_password: '',
    confirm_password: '',
  })
  const [userPasswordSaving, setUserPasswordSaving] = useState(false)
  const [userPasswordMessage, setUserPasswordMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [formData, setFormData] = useState<WorkspaceFormData>({
    workspace_name: '',
    subdomain_prefix: '',
    admin_email: '',
    admin_password: '',
    admin_full_name: '',
    admin_language: 'ru',
  })
  
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const { t } = useI18n()

  // 1. Fetch Data Function (Reusable)
  const fetchWorkspaces = (token: string) => {
    axios.get('/superadmin/workspaces', {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => {
      setWorkspaces(res.data || [])
      setLoading(false)
    })
    .catch(err => console.error(err))
  }

  const fetchModuleDefinitions = async (token: string) => {
    const res = await axios.get('/modules/definitions', {
      headers: { Authorization: `Bearer ${token}` }
    })
    setModuleDefinitions(Array.isArray(res.data) ? res.data : [])
  }

  const fetchAiSettings = async (token: string) => {
    const res = await axios.get('/superadmin/ai-settings', {
      headers: { Authorization: `Bearer ${token}` }
    })
    const nextSettings = res.data as AiSettings
    setAiSettings(nextSettings)
    setAiDraft({
      provider: nextSettings.provider || 'deterministic',
      model: nextSettings.model || '',
      base_url: nextSettings.base_url || '',
      api_key: '',
    })
  }

  const fetchWorkspaceUsers = async (workspaceId: string) => {
    const token = localStorage.getItem('crm_token')
    if (!token || !workspaceId) return
    setWorkspaceUsersLoading(true)
    setUserPasswordMessage(null)
    try {
      const res = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` },
        params: { workspace_id: workspaceId, limit: 500 },
      })
      const users = Array.isArray(res.data) ? res.data as WorkspaceUser[] : []
      setWorkspaceUsers(users)
      setUserPasswordDraft(prev => ({
        ...prev,
        user_id: users.some(user => user.id === prev.user_id) ? prev.user_id : users[0]?.id || '',
      }))
    } catch (err: any) {
      setWorkspaceUsers([])
      setUserPasswordDraft(prev => ({ ...prev, user_id: '' }))
      setUserPasswordMessage({ type: 'error', text: err.response?.data?.detail || t('super.passwordResetFailed') })
    } finally {
      setWorkspaceUsersLoading(false)
    }
  }

  const handleSuspend = async (workspaceId: string) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    if (!confirm(t('super.suspendConfirm'))) return
    await axios.post(`/superadmin/workspaces/${workspaceId}/suspend`, null, {
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchWorkspaces(token)
  }

  const handleActivate = async (workspaceId: string) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    await axios.put(`/superadmin/workspaces/${workspaceId}/activate`, null, {
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchWorkspaces(token)
  }

  const handleRename = async (workspaceId: string, currentName: string) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    const newName = prompt(t('super.newWorkspaceName'), currentName)
    if (!newName || newName.trim() === currentName) return
    await axios.put(`/superadmin/workspaces/${workspaceId}`, {
      workspace_name: newName.trim()
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchWorkspaces(token)
  }

  const openModuleModal = (workspace: any) => {
    const settings = getWorkspaceModuleSettings(workspace)
    setModuleModalWorkspace(workspace)
    setModuleDraftEnabled(settings.enabled_modules)
  }

  const closeModuleModal = () => {
    setModuleModalWorkspace(null)
    setModuleDraftEnabled([])
    setModuleSaving(false)
  }

  const toggleModule = (moduleId: string) => {
    setModuleDraftEnabled(prev => (
      prev.includes(moduleId)
        ? prev.filter(item => item !== moduleId)
        : [...prev, moduleId]
    ))
  }

  const saveWorkspaceModules = async () => {
    if (!moduleModalWorkspace) return
    const token = localStorage.getItem('crm_token')
    if (!token) return
    setModuleSaving(true)
    try {
      await axios.put(`/superadmin/workspaces/${moduleModalWorkspace.id}/modules`, {
        module_preset: 'functional',
        enabled_modules: moduleDraftEnabled,
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      window.dispatchEvent(new CustomEvent('crm:workspace-modules-updated', {
        detail: {
          workspaceId: moduleModalWorkspace.id,
          enabledModules: moduleDraftEnabled,
        },
      }))
      closeModuleModal()
      fetchWorkspaces(token)
    } catch (err: any) {
      alert(err.response?.data?.detail || t('super.moduleSaveFailed'))
      setModuleSaving(false)
    }
  }

  const handleSaveAiSettings = async (event: React.FormEvent) => {
    event.preventDefault()
    const token = localStorage.getItem('crm_token')
    if (!token) return

    const provider = aiDraft.provider.trim()
    const model = aiDraft.model.trim()
    const apiKey = aiDraft.api_key.trim()
    const isLiveProvider = provider === 'gemini' || provider === 'grok'
    if (isLiveProvider && (!model || (!apiKey && !aiSettings?.api_key_configured))) {
      setAiMessage({ type: 'error', text: t('super.liveProviderRequirements') })
      return
    }

    setAiSaving(true)
    setAiMessage(null)
    try {
      const payload: {
        provider: string;
        model: string;
        base_url: string;
        api_key?: string;
      } = {
        provider,
        model,
        base_url: aiDraft.base_url.trim(),
      }
      if (apiKey) {
        payload.api_key = apiKey
      }
      const res = await axios.put('/superadmin/ai-settings', payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const nextSettings = res.data as AiSettings
      setAiSettings(nextSettings)
      setAiDraft({
        provider: nextSettings.provider || 'deterministic',
        model: nextSettings.model || '',
        base_url: nextSettings.base_url || '',
        api_key: '',
      })
      setAiMessage({ type: 'success', text: t('super.aiProviderSaved') })
    } catch (err: any) {
      setAiMessage({ type: 'error', text: err.response?.data?.detail || t('super.aiProviderFailed') })
    } finally {
      setAiSaving(false)
    }
  }

  const handleResetWorkspaceUserPassword = async (event: React.FormEvent) => {
    event.preventDefault()
    const token = localStorage.getItem('crm_token')
    if (!token) return

    if (!userPasswordDraft.user_id) {
      setUserPasswordMessage({ type: 'error', text: t('super.selectUserFirst') })
      return
    }

    if (userPasswordDraft.new_password !== userPasswordDraft.confirm_password) {
      setUserPasswordMessage({ type: 'error', text: t('super.passwordMismatch') })
      return
    }

    if (userPasswordDraft.new_password.length < 8) {
      setUserPasswordMessage({ type: 'error', text: t('super.passwordTooShort') })
      return
    }

    const selectedUser = workspaceUsers.find(user => user.id === userPasswordDraft.user_id)
    setUserPasswordSaving(true)
    setUserPasswordMessage(null)
    try {
      await axios.put(`/access/users/${userPasswordDraft.user_id}/password`, {
        new_password: userPasswordDraft.new_password,
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUserPasswordDraft(prev => ({ ...prev, new_password: '', confirm_password: '' }))
      setUserPasswordMessage({ type: 'success', text: `${t('super.passwordReset')}${selectedUser ? `: ${selectedUser.full_name}` : ''}.` })
    } catch (err: any) {
      setUserPasswordMessage({ type: 'error', text: err.response?.data?.detail || t('super.passwordResetFailed') })
    } finally {
      setUserPasswordSaving(false)
    }
  }

  // 2. Initial Load Effect
  useEffect(() => {
    const token = localStorage.getItem('crm_token')
    if (!token) { navigate('/'); return }

    axios.get('/access/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => {
      setCurrentUser(res.data)
      // Strict Check
      const role = res.data.role?.toUpperCase() || ''
      if (role !== 'SUPERADMIN') {
        setError('Access Denied: Superadmin privileges required')
        setTimeout(() => navigate('/dashboard'), 2000)
        return
      }
      fetchModuleDefinitions(token).catch(err => console.error(err))
      fetchAiSettings(token).catch(err => {
        console.error(err)
        setAiMessage({ type: 'error', text: t('super.aiProviderFailed') })
      })
      fetchWorkspaces(token)
    })
    .catch(err => {
      console.error(err)
      setError('Failed to authenticate')
      setLoading(false)
    })
  }, [navigate, t])

  useEffect(() => {
    if (!selectedPasswordWorkspaceId && workspaces.length > 0) {
      setSelectedPasswordWorkspaceId(workspaces[0].id)
    }
  }, [selectedPasswordWorkspaceId, workspaces])

  useEffect(() => {
    if (!selectedPasswordWorkspaceId) return
    void fetchWorkspaceUsers(selectedPasswordWorkspaceId)
  }, [selectedPasswordWorkspaceId])

  // 3. Handle Create Submission
  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsCreating(true)
    const token = localStorage.getItem('crm_token')

    try {
      // We send all data to the Superadmin "Composite" endpoint
      await axios.post('/superadmin/workspaces', formData, {
        headers: { Authorization: `Bearer ${token}` }
      })

      // Success!
      alert(`✅ ${t('super.workspaceCreated')}: "${formData.workspace_name}"`)
      setShowModal(false)
      // Reset Form
      setFormData({ workspace_name: '', subdomain_prefix: '', admin_email: '', admin_password: '', admin_full_name: '', admin_language: 'ru' })
      // Refresh List
      if (token) fetchWorkspaces(token)

    } catch (err: any) {
      console.error(err)
      alert(err.response?.data?.detail || t('super.workspaceCreateFailed'))
    } finally {
      setIsCreating(false)
    }
  }

  const groupedModuleDefinitions = useMemo(() => {
    return moduleDefinitions.reduce<Record<string, ModuleDefinition[]>>((acc, definition) => {
      const category = definition.category || 'functional'
      acc[category] = acc[category] || []
      acc[category].push(definition)
      return acc
    }, {})
  }, [moduleDefinitions])

  const selectedPasswordWorkspace = useMemo(
    () => workspaces.find(workspace => workspace.id === selectedPasswordWorkspaceId) || null,
    [selectedPasswordWorkspaceId, workspaces],
  )

  const selectedPasswordUser = useMemo(
    () => workspaceUsers.find(user => user.id === userPasswordDraft.user_id) || null,
    [userPasswordDraft.user_id, workspaceUsers],
  )

  // --- RENDER HELPERS ---
  if (error) return <div style={{ padding: isMobile ? '16px' : '50px', textAlign: 'center', color: theme.colors.error }}>🚫 {error}</div>
  if (!currentUser || loading) return <div style={{ padding: isMobile ? '16px' : '50px', textAlign: 'center' }}>{t('common.loading')}</div>

  return (
    <div className="crm-page-shell" style={{ maxWidth: '1400px', margin: '0 auto', padding: isMobile ? '16px' : '40px', fontFamily: 'sans-serif', position: 'relative' }}>
      
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px',
        marginBottom: '40px', paddingBottom: '20px', borderBottom: `2px solid ${theme.colors.error}`
      }}>
        <button
          onClick={() => navigate('/home')}
          style={{
          background: 'transparent',
          border: `1px solid ${theme.colors.gray.border}`,
          padding: '8px 14px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontSize: '14px',
          color: theme.colors.gray.textLight,
          boxShadow: theme.shadows.sm,
          width: isMobile ? '100%' : 'auto'
        }}
        >
          ← {t('common.backHome')}
        </button>

        <div>
          <h1 style={{ margin: 0, color: theme.colors.error }}>🔐 {t('super.title')}</h1>
          <p style={{ color: theme.colors.gray.textLight }}>{t('super.subtitle')}</p>
        </div>
        <div style={{ textAlign: isMobile ? 'left' : 'right' }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>{currentUser.full_name}</p>
          <span style={{ fontSize: '12px', background: theme.colors.error, color: 'white', padding: '2px 6px', borderRadius: '4px' }}>SUPERADMIN</span>
        </div>
      </div>

      <div className="crm-superadmin-config">
        <section className="crm-superadmin-panel" aria-label={t('super.aiProvider')}>
          <div className="crm-superadmin-panel-head">
            <h2>{t('super.aiProvider')}</h2>
            <span className={`pill ${aiSettings?.provider === 'deterministic' ? 'pill--neutral' : 'pill--success'}`}>
              {aiSettings?.provider === 'deterministic'
                ? 'Deterministic'
                : aiSettings?.api_key_configured
                  ? `Connected ${aiSettings.api_key_preview || ''}`.trim()
                  : 'Not connected'}
            </span>
          </div>

          <form className="crm-superadmin-form" onSubmit={handleSaveAiSettings}>
            <div className="crm-superadmin-form-grid">
              <label className="field">
                <span className="field-label">{t('super.provider')}</span>
                <select
                  className="select"
                  value={aiDraft.provider}
                  onChange={event => setAiDraft(prev => ({ ...prev, provider: event.target.value }))}
                >
                  <option value="deterministic">Deterministic</option>
                  <option value="gemini">Gemini</option>
                  <option value="grok">Grok</option>
                </select>
              </label>

              <label className="field">
                <span className="field-label">{t('super.model')}</span>
                <input
                  className="input"
                  value={aiDraft.model}
                  onChange={event => setAiDraft(prev => ({ ...prev, model: event.target.value }))}
                  placeholder="gemini-1.5-pro"
                />
              </label>

              <label className="field">
                <span className="field-label">{t('super.baseUrl')}</span>
                <input
                  className="input"
                  value={aiDraft.base_url}
                  onChange={event => setAiDraft(prev => ({ ...prev, base_url: event.target.value }))}
                  placeholder="Default provider URL"
                />
              </label>

              <label className="field">
                <span className="field-label">{t('super.apiKey')}</span>
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  value={aiDraft.api_key}
                  onChange={event => setAiDraft(prev => ({ ...prev, api_key: event.target.value }))}
                  placeholder={aiSettings?.api_key_configured ? aiSettings.api_key_preview || 'Saved key' : 'Provider key'}
                />
              </label>
            </div>

            <div className="crm-superadmin-form-footer">
              {aiMessage && (
                <p className={`crm-form-message is-${aiMessage.type}`}>{aiMessage.text}</p>
              )}
              <button className="btn btn--primary" type="submit" disabled={aiSaving}>
                {aiSaving ? `${t('common.save')}...` : t('super.saveAiProvider')}
              </button>
            </div>
          </form>
        </section>

        <section className="crm-superadmin-panel" aria-label={t('super.userPasswords')}>
          <div className="crm-superadmin-panel-head">
            <h2>{t('super.userPasswords')}</h2>
            <span className="pill pill--neutral">
              {selectedPasswordWorkspace ? selectedPasswordWorkspace.name : t('common.workspace')}
            </span>
          </div>

          <p className="crm-superadmin-note">{t('super.userPasswordsNote')}</p>

          <form className="crm-superadmin-form" onSubmit={handleResetWorkspaceUserPassword}>
            <div className="crm-superadmin-form-grid">
              <label className="field">
                <span className="field-label">{t('common.workspace')}</span>
                <select
                  className="select"
                  value={selectedPasswordWorkspaceId}
                  onChange={event => {
                    setSelectedPasswordWorkspaceId(event.target.value)
                    setUserPasswordDraft({ user_id: '', new_password: '', confirm_password: '' })
                  }}
                >
                  {workspaces.map(workspace => (
                    <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span className="field-label">{t('common.user')}</span>
                <select
                  className="select"
                  value={userPasswordDraft.user_id}
                  onChange={event => setUserPasswordDraft(prev => ({ ...prev, user_id: event.target.value }))}
                  disabled={workspaceUsersLoading || workspaceUsers.length === 0}
                >
                  {workspaceUsers.length === 0 && (
                    <option value="">{workspaceUsersLoading ? t('super.loadingUsers') : t('super.noUsers')}</option>
                  )}
                  {workspaceUsers.map(user => (
                    <option key={user.id} value={user.id}>
                      {user.full_name} · {user.email}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span className="field-label">{t('super.newTemporaryPassword')}</span>
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  value={userPasswordDraft.new_password}
                  onChange={event => setUserPasswordDraft(prev => ({ ...prev, new_password: event.target.value }))}
                  required
                  minLength={8}
                />
              </label>

              <label className="field">
                <span className="field-label">{t('super.confirmTemporaryPassword')}</span>
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  value={userPasswordDraft.confirm_password}
                  onChange={event => setUserPasswordDraft(prev => ({ ...prev, confirm_password: event.target.value }))}
                  required
                  minLength={8}
                />
              </label>
            </div>

            {selectedPasswordUser && (
              <div className="crm-password-user">
                <strong>{selectedPasswordUser.full_name}</strong>
                <span>{selectedPasswordUser.email}</span>
                <span>{selectedPasswordUser.role}</span>
              </div>
            )}

            <div className="crm-superadmin-form-footer">
              {userPasswordMessage && (
                <p className={`crm-form-message is-${userPasswordMessage.type}`}>{userPasswordMessage.text}</p>
              )}
              <button className="btn btn--primary" type="submit" disabled={userPasswordSaving || workspaceUsersLoading || workspaceUsers.length === 0}>
                {userPasswordSaving ? t('super.resettingPassword') : t('super.resetPassword')}
              </button>
            </div>
          </form>
        </section>
      </div>

      {/* Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
        <button
          onClick={() => setShowModal(true)}
          style={{
            background: theme.colors.error, color: 'white', border: 'none',
            padding: '12px 24px', borderRadius: '6px', cursor: 'pointer',
            fontSize: '16px', fontWeight: 'bold', boxShadow: theme.shadows.md,
            width: isMobile ? '100%' : 'auto'
          }}
        >
          + {t('super.newWorkspace')}
        </button>
      </div>

      {/* Workspaces List Table */}
      <div style={{ background: 'white', borderRadius: '8px', overflow: 'hidden', boxShadow: theme.shadows.md, border: `1px solid ${theme.colors.gray.border}` }}>
        <div style={{ background: '#333', color: 'white', padding: '15px 20px', fontWeight: 'bold' }}>
          📊 {t('super.activeWorkspaces')} ({workspaces.length})
        </div>
        <div className="crm-table-scroll">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: theme.colors.gray.light, borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '15px', textAlign: 'left' }}>{t('super.company')}</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>{t('super.subdomain')}</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>{t('super.adminContact')}</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>{t('super.modules')}</th>
              <th style={{ padding: '15px', textAlign: 'left' }}>{t('common.status')}</th>
              <th style={{ padding: '15px', textAlign: 'center' }}>{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {workspaces.map(ws => (
              <tr key={ws.id} style={{ borderBottom: `1px solid ${theme.colors.gray.border}` }}>
                <td style={{ padding: '15px', fontWeight: 'bold' }}>{ws.name}</td>
                <td style={{ padding: '15px' }}><code style={{ background: '#eee', padding: '4px' }}>{ws.subdomain_prefix}</code></td>
                <td style={{ padding: '15px' }}>{ws.admin_email}</td>
                <td style={{ padding: '15px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <button onClick={() => openModuleModal(ws)}>
                      {t('super.manageModules')} ({getWorkspaceModuleSettings(ws).enabled_modules.length})
                    </button>
                  </div>
                </td>
                <td style={{ padding: '15px' }}>
                  <span style={{ color: ws.is_active ? theme.colors.success : theme.colors.error, fontWeight: 'bold' }}>
                    ● {ws.is_active ? t('common.active') : t('common.suspended')}
                  </span>
                </td>
                <td style={{ padding: '15px', textAlign: 'center' }}>
                  <button
                    onClick={() => handleRename(ws.id, ws.name)}
                    style={{ marginRight: '8px' }}
                  >
                    {t('super.rename')}
                  </button>
                  {ws.is_active ? (
                    <button onClick={() => handleSuspend(ws.id)}>{t('super.suspend')}</button>
                  ) : (
                    <button onClick={() => handleActivate(ws.id)}>{t('super.activate')}</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>

      {/* --- CREATE WORKSPACE MODAL --- */}
      {showModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: isMobile ? 'flex-start' : 'center', zIndex: 1000, padding: isMobile ? '16px' : '0'
        }}>
          <div style={{
            background: 'white', padding: '30px', borderRadius: '10px',
            width: 'min(500px, 100%)', boxShadow: theme.shadows.lg, position: 'relative', marginTop: isMobile ? '20px' : 0
          }}>
            <h2 style={{ marginTop: 0, borderBottom: '1px solid #eee', paddingBottom: '15px' }}>🚀 {t('super.launchWorkspace')}</h2>
            
            <form onSubmit={handleCreateWorkspace} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '20px' }}>
              
              {/* Company Info */}
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '15px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{t('super.companyName')}</label>
                  <input required placeholder="e.g. Tesla Inc." 
                    value={formData.workspace_name} onChange={e => setFormData({...formData, workspace_name: e.target.value})}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{t('super.subdomain')}</label>
                  <input required placeholder="e.g. tesla" 
                    value={formData.subdomain_prefix} onChange={e => setFormData({...formData, subdomain_prefix: e.target.value.toLowerCase()})}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>
              </div>

              {/* Admin Info */}
              <div style={{ borderTop: '1px solid #eee', paddingTop: '15px', marginTop: '5px' }}>
                <label style={{ fontSize: '12px', color: 'gray', marginBottom: '10px', display: 'block' }}>{t('super.initialAdmin')}</label>
                
                <div style={{ marginBottom: '10px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{t('admin.fullName')}</label>
                  <input required placeholder="e.g. Elon Musk" 
                    value={formData.admin_full_name} onChange={e => setFormData({...formData, admin_full_name: e.target.value})}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>

                <div style={{ marginBottom: '10px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{t('super.emailAddress')}</label>
                  <input required type="email" placeholder="admin@tesla.com" 
                    value={formData.admin_email} onChange={e => setFormData({...formData, admin_email: e.target.value})}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>

                <div style={{ marginBottom: '10px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{t('common.password')}</label>
                  <input required type="password" placeholder="Min 8 chars" 
                    value={formData.admin_password} onChange={e => setFormData({...formData, admin_password: e.target.value})}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }} />
                </div>

                <div>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px' }}>{t('common.language')}</label>
                  <select
                    value={formData.admin_language}
                    onChange={e => setFormData({...formData, admin_language: normalizeLanguage(e.target.value)})}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                  >
                    {LANGUAGE_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Buttons */}
              <div className={isMobile ? 'crm-mobile-stack' : ''} style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button type="button" onClick={() => setShowModal(false)}
                  style={{ flex: 1, padding: '10px', background: '#ccc', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                  {t('common.cancel')}
                </button>
                <button type="submit" disabled={isCreating}
                  style={{ flex: 1, padding: '10px', background: theme.colors.error, color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', opacity: isCreating ? 0.7 : 1 }}>
                  {isCreating ? t('super.creatingWorkspace') : t('super.createWorkspace')}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {moduleModalWorkspace && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: isMobile ? 'flex-start' : 'center', zIndex: 1000, padding: isMobile ? '16px' : '0'
        }}>
          <div style={{
            background: 'white',
            padding: '28px',
            borderRadius: '10px',
            width: 'min(760px, 100%)',
            maxHeight: isMobile ? 'calc(100vh - 32px)' : '86vh',
            overflow: 'auto',
            boxShadow: theme.shadows.lg,
            marginTop: isMobile ? '20px' : 0
          }}>
            <h2 style={{ marginTop: 0 }}>{t('super.workspaceModules')}</h2>
            <p style={{ marginTop: 0, color: theme.colors.gray.textLight }}>
              {moduleModalWorkspace.name}
            </p>

            {Object.entries(groupedModuleDefinitions).map(([category, definitions]) => (
              <section key={category} style={{ marginBottom: '22px' }}>
                <h3 style={{ margin: '0 0 10px', fontSize: '15px' }}>
                  {t('modules.coreModules')}
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '10px' }}>
                  {definitions.map(definition => {
                    const checked = moduleDraftEnabled.includes(definition.id)
                    const synergies = definition.synergies || []
                    return (
                      <label
                        key={definition.id}
                        style={{
                          border: `1px solid ${checked ? theme.colors.black : theme.colors.gray.border}`,
                          borderRadius: '8px',
                          padding: '12px',
                          display: 'flex',
                          gap: '10px',
                          alignItems: 'flex-start',
                          cursor: 'pointer',
                          background: checked ? '#f7f7f7' : '#fff'
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleModule(definition.id)}
                          style={{ marginTop: '3px' }}
                        />
                        <span>
                          <strong style={{ display: 'block' }}>{definition.label}</strong>
                          <span style={{ display: 'block', color: theme.colors.gray.textLight, fontSize: '12px', lineHeight: 1.4 }}>
                            {definition.description}
                          </span>
                          {synergies.length > 0 && (
                            <span style={{ display: 'block', color: theme.colors.gray.textLight, fontSize: '11px', marginTop: '6px' }}>
                              {t('super.synergies')}: {synergies.map(synergy => synergy.label).join(', ')}
                            </span>
                          )}
                        </span>
                      </label>
                    )
                  })}
                </div>
              </section>
            ))}

            <div className={isMobile ? 'crm-mobile-stack' : ''} style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
              <button
                type="button"
                onClick={closeModuleModal}
                style={{ flex: 1, padding: '10px', background: '#ccc', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                disabled={moduleSaving}
                onClick={saveWorkspaceModules}
                style={{ flex: 1, padding: '10px', background: theme.colors.error, color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', opacity: moduleSaving ? 0.7 : 1 }}
              >
                {moduleSaving ? `${t('common.save')}...` : t('super.saveModules')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default WorkspaceManagementPage
