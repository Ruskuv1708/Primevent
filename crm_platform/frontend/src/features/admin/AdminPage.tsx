import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ROLE_DISPLAY_NAMES, roleMatches } from '../../shared/roleLabels'
import useIsMobile from '../../shared/useIsMobile'
import { useI18n } from '../../shared/i18nContext'
import { LANGUAGE_OPTIONS, normalizeLanguage, type AppLanguage } from '../../shared/language'
import type { FormTemplate } from '../forms/types'
import { formFieldVisibilityKey } from '../../shared/roleVisibility'

interface User {
  id: string
  full_name: string
  email: string
  role: 'SUPERADMIN' | 'SYSTEM_ADMIN' | 'ADMIN' | 'MANAGER' | 'USER' | 'VIEWER'
  language: AppLanguage
  is_active: boolean
  workspace_id: string | null
  department_id: string | null
  custom_role_id?: string | null
  custom_role?: WorkspaceCustomRole | null
}

interface Workspace {
  id: string
  name: string
  is_active: boolean
}

interface Department {
  id: string
  name: string
  description?: string | null
}

type RolePermissions = {
  tabs: Record<string, boolean>
  fields: Record<string, Record<string, boolean>>
}

interface WorkspaceCustomRole {
  id: string
  workspace_id: string
  name: string
  description?: string | null
  base_role: string
  permissions: RolePermissions
}

const TAB_PERMISSION_OPTIONS = [
  { key: 'home', labelKey: 'nav.home' },
  { key: 'people', labelKey: 'nav.people' },
  { key: 'work', labelKey: 'nav.work' },
  { key: 'employee_evaluations', labelKey: 'nav.employeeEvaluations' },
  { key: 'money', labelKey: 'nav.money' },
  { key: 'reports', labelKey: 'nav.reports' },
  { key: 'settings', labelKey: 'nav.settings' },
  { key: 'ai_architect', labelKey: 'nav.aiArchitect' },
  { key: 'admin', labelKey: 'nav.admin' },
  { key: 'superadmin', labelKey: 'nav.superadmin' },
]

const defaultRolePermissions = (): RolePermissions => ({
  tabs: {
    home: true,
    people: true,
    work: true,
    employee_evaluations: true,
    money: true,
    reports: true,
    settings: true,
    ai_architect: false,
    admin: false,
    superadmin: false,
  },
  fields: {
    forms: {},
  },
})

const normalizePermissions = (permissions?: Partial<RolePermissions> | null): RolePermissions => {
  const defaults = defaultRolePermissions()
  return {
    tabs: { ...defaults.tabs, ...(permissions?.tabs || {}) },
    fields: {
      forms: { ...(permissions?.fields?.forms || {}) },
    },
  }
}

const normalizeWorkspaceRole = (role: any): WorkspaceCustomRole => ({
  ...role,
  base_role: normalizeUserRole(role.base_role),
  permissions: normalizePermissions(role.permissions),
})

const normalizeUserRole = (role?: string) => (role || '').toUpperCase()

const ROLE_DISPLAY_NAMES_RU: Record<string, string> = {
  SUPERADMIN: 'Суперадмин',
  SYSTEM_ADMIN: 'Системный админ',
  ADMIN: 'Администратор',
  MANAGER: 'Менеджер отдела',
  USER: 'Пользователь',
  VIEWER: 'Наблюдатель',
}

function AdminPage() {
  const { language, t } = useI18n()
  const [users, setUsers] = useState<User[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [workspaceRoles, setWorkspaceRoles] = useState<WorkspaceCustomRole[]>([])
  const [formTemplates, setFormTemplates] = useState<FormTemplate[]>([])
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>(() => {
    try {
      return localStorage.getItem('crm_workspace_id') || ''
    } catch {
      return ''
    }
  })
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const getRoleDisplayName = (role: string) => (
    language === 'ru' ? ROLE_DISPLAY_NAMES_RU[role] ?? role : ROLE_DISPLAY_NAMES[role] ?? role
  )

  const [newUser, setNewUser] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'USER',
    language,
    workspace_id: '',
    department_id: '',
    custom_role_id: ''
  })

  const [roleDraft, setRoleDraft] = useState({
    id: '',
    name: '',
    description: '',
    base_role: 'USER',
    permissions: defaultRolePermissions(),
  })

  const [newDept, setNewDept] = useState({ name: '', description: '' })
  const [editDeptId, setEditDeptId] = useState<string | null>(null)
  const [editDeptName, setEditDeptName] = useState('')
  const [editDeptDescription, setEditDeptDescription] = useState('')

  const getRoleOptions = (role: string) => {
    if (roleMatches(role, ['SUPERADMIN', 'SYSTEM_ADMIN'])) {
      return ['VIEWER', 'USER', 'MANAGER', 'ADMIN', 'SYSTEM_ADMIN']
    }
    if (roleMatches(role, ['ADMIN'])) {
      return ['VIEWER', 'USER', 'MANAGER']
    }
    if (roleMatches(role, ['MANAGER'])) {
      return ['VIEWER', 'USER']
    }
    return ['VIEWER', 'USER']
  }

  const getRoleOptionsForCreation = (role: string) => getRoleOptions(role)
  const getRoleOptionsForEdit = (role: string) => getRoleOptions(role)
  const resolveRoleOptions = (targetRole: string) => {
    const editorRole = currentUser?.role || 'ADMIN'
    const baseOptions = getRoleOptionsForEdit(editorRole)
    const normalizedTarget = targetRole.toUpperCase()
    return baseOptions.includes(normalizedTarget) ? baseOptions : [...baseOptions, normalizedTarget]
  }

  const normalizeUser = (user: any) => ({
    ...user,
    role: normalizeUserRole(user.role),
    language: normalizeLanguage(user.language),
    custom_role: user.custom_role ? normalizeWorkspaceRole(user.custom_role) : null,
  })

  useEffect(() => {
    let active = true
    const token = localStorage.getItem('crm_token')
    if (!token) {
      navigate('/')
      return
    }

    const loadAdminData = async () => {
      const currentUserRes = await axios.get('/access/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      const normalized = normalizeUser(currentUserRes.data)
      if (!active) return
      setCurrentUser(normalized)

      if (!roleMatches(normalized.role, ['ADMIN', 'SUPERADMIN', 'SYSTEM_ADMIN'])) {
        navigate('/dashboard')
        return
      }

      setSelectedWorkspace(currentUserRes.data.workspace_id)

      let workspaceRes = null
      if (roleMatches(normalized.role, ['SUPERADMIN','SYSTEM_ADMIN'])) {
        workspaceRes = await axios.get('/superadmin/workspaces', {
          headers: { Authorization: `Bearer ${token}` }
        })
      } else if (currentUserRes.data.workspace_id) {
        workspaceRes = await axios.get(`/superadmin/workspaces/${currentUserRes.data.workspace_id}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }

      if (!active) return
      if (workspaceRes?.data) {
        setWorkspaces(Array.isArray(workspaceRes.data) ? workspaceRes.data : [workspaceRes.data])
      }

      const usersRes = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!active) return
      setUsers((usersRes.data || []).map((user: any) => normalizeUser(user)))
    }

    loadAdminData()
      .catch(err => {
        console.error(err)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [navigate])

  useEffect(() => {
    const token = localStorage.getItem('crm_token')
    if (!token) return

    const params = roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN']) && selectedWorkspace
      ? { workspace_id: selectedWorkspace }
      : undefined

    axios.get('/workflow/departments', {
      headers: { Authorization: `Bearer ${token}` },
      params
    })
    .then(res => setDepartments(res.data))
    .catch(err => console.error(err))
  }, [currentUser?.role, selectedWorkspace])

  useEffect(() => {
    if (!currentUser) return
    if (roleMatches(currentUser.role, ['SUPERADMIN','SYSTEM_ADMIN'])) {
      setNewUser(prev => ({ ...prev, workspace_id: selectedWorkspace || '' }))
    } else {
      setNewUser(prev => ({ ...prev, workspace_id: currentUser.workspace_id || '' }))
    }
  }, [currentUser, selectedWorkspace])

  useEffect(() => {
    if (roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN']) && !selectedWorkspace && workspaces.length > 0) {
      setSelectedWorkspace(workspaces[0].id)
    }
  }, [currentUser?.role, selectedWorkspace, workspaces])

  useEffect(() => {
    if (!roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN'])) return
    if (!selectedWorkspace) return
    try {
      localStorage.setItem('crm_workspace_id', selectedWorkspace)
    } catch {
      // ignore storage errors
    }
  }, [currentUser?.role, selectedWorkspace])

  const getWorkspaceParams = () => {
    if (roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN']) && selectedWorkspace) {
      return { workspace_id: selectedWorkspace }
    }
    return undefined
  }

  const getRoleWorkspaceId = () => (
    roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN'])
      ? selectedWorkspace
      : currentUser?.workspace_id || ''
  )

  const refreshWorkspaceRoles = async () => {
    const token = localStorage.getItem('crm_token')
    const workspaceId = getRoleWorkspaceId()
    if (!token || !workspaceId) {
      setWorkspaceRoles([])
      return
    }
    const res = await axios.get('/access/workspace-roles', {
      headers: { Authorization: `Bearer ${token}` },
      params: roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN']) ? { workspace_id: workspaceId } : undefined,
    })
    setWorkspaceRoles((res.data || []).map((role: any) => normalizeWorkspaceRole(role)))
  }

  const refreshFormTemplates = async () => {
    const token = localStorage.getItem('crm_token')
    const workspaceId = getRoleWorkspaceId()
    if (!token || !workspaceId) {
      setFormTemplates([])
      return
    }
    const res = await axios.get('/forms/templates', {
      headers: { Authorization: `Bearer ${token}` },
      params: getWorkspaceParams(),
    })
    setFormTemplates(res.data || [])
  }

  const resetRoleDraft = () => {
    setRoleDraft({
      id: '',
      name: '',
      description: '',
      base_role: 'USER',
      permissions: defaultRolePermissions(),
    })
  }

  const handleToggleTabPermission = (tabKey: string, value: boolean) => {
    setRoleDraft(prev => ({
      ...prev,
      permissions: {
        ...prev.permissions,
        tabs: { ...prev.permissions.tabs, [tabKey]: value },
      },
    }))
  }

  const handleToggleFieldPermission = (templateId: string, fieldKey: string, value: boolean) => {
    const visibilityKey = formFieldVisibilityKey(templateId, fieldKey)
    setRoleDraft(prev => ({
      ...prev,
      permissions: {
        ...prev.permissions,
        fields: {
          ...prev.permissions.fields,
          forms: {
            ...(prev.permissions.fields.forms || {}),
            [visibilityKey]: value,
          },
        },
      },
    }))
  }

  useEffect(() => {
    if (!currentUser) return
    if (!getRoleWorkspaceId()) return
    refreshWorkspaceRoles().catch(err => console.error(err))
    refreshFormTemplates().catch(err => console.warn('Unable to load form templates for role visibility', err))
  }, [currentUser?.role, currentUser?.workspace_id, selectedWorkspace])

  const handleCreateDepartment = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem('crm_token')
    if (!token) return
    if (roleMatches(currentUser?.role, ['SUPERADMIN','SYSTEM_ADMIN']) && !selectedWorkspace) {
      alert(t('admin.selectWorkspace'))
      return
    }
    try {
      await axios.post('/workflow/departments', newDept, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams()
      })
      setNewDept({ name: '', description: '' })
      const res = await axios.get('/workflow/departments', {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams()
      })
      setDepartments(res.data)
    } catch (err: any) {
      alert(err.response?.data?.detail || t('admin.createFailed'))
    }
  }

  const handleUpdateDepartment = async (deptId: string) => {
    const token = localStorage.getItem('crm_token')
    try {
      await axios.put(
        `/workflow/departments/${deptId}`,
        { name: editDeptName, description: editDeptDescription },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: getWorkspaceParams()
        }
      )
      setEditDeptId(null)
      const res = await axios.get('/workflow/departments', {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams()
      })
      setDepartments(res.data)
    } catch (err: any) {
      alert(err.response?.data?.detail || t('profile.updateFailed'))
    }
  }

  const handleUpdateUserDepartment = async (userId: string, departmentId: string | null) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    try {
      await axios.put(
        `/access/users/${userId}`,
        { department_id: departmentId || null },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const res = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(res.data.map((user: any) => normalizeUser(user)))
    } catch (err: any) {
      alert(err.response?.data?.detail || t('admin.departmentUpdateFailed'))
    }
  }

  const handleDeleteDepartment = async (deptId: string) => {
    const token = localStorage.getItem('crm_token')
    if (!confirm(t('admin.deleteDepartmentConfirm'))) return
    try {
      await axios.delete(`/workflow/departments/${deptId}`, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams()
      })
      setDepartments(prev => prev.filter(d => d.id !== deptId))
    } catch (err: any) {
      alert(err.response?.data?.detail || t('profile.updateFailed'))
    }
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem('crm_token')
    
    if (!roleMatches(newUser.role, ['SUPERADMIN','SYSTEM_ADMIN']) && !newUser.workspace_id) {
      alert(t('admin.selectWorkspace'))
      return
    }
    if (roleMatches(newUser.role, ['MANAGER','USER']) && !newUser.department_id) {
      alert(t('admin.selectDepartmentPlaceholder'))
      return
    }

    try {
      // Create user with workspace_id
      await axios.post(
        '/access/users',
        {
          full_name: newUser.full_name,
          email: newUser.email,
          password: newUser.password,
          role: newUser.role,
          language: newUser.language,
          workspace_id: newUser.workspace_id,
          department_id: newUser.department_id || null,
          custom_role_id: newUser.custom_role_id || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      )

      // Refresh users list
      const res = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(res.data.map((user: any) => normalizeUser(user)))
      
      setNewUser({
        full_name: '',
        email: '',
        password: '',
        role: 'USER',
        language,
        workspace_id: selectedWorkspace,
        department_id: '',
        custom_role_id: ''
      })
      setShowCreateForm(false)
      alert(t('admin.userCreated'))
    } catch (err: any) {
      alert(err.response?.data?.detail || t('admin.createFailed'))
    }
  }

  const handleSaveWorkspaceRole = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem('crm_token')
    const workspaceId = getRoleWorkspaceId()
    if (!token || !workspaceId) return
    if (!roleDraft.name.trim()) {
      alert(t('admin.roleNameRequired'))
      return
    }

    const payload = {
      workspace_id: workspaceId,
      name: roleDraft.name,
      description: roleDraft.description,
      base_role: roleDraft.base_role,
      permissions: roleDraft.permissions,
    }

    try {
      if (roleDraft.id) {
        await axios.put(`/access/workspace-roles/${roleDraft.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` },
        })
        alert(t('admin.accessProfileUpdated'))
      } else {
        await axios.post('/access/workspace-roles', payload, {
          headers: { Authorization: `Bearer ${token}` },
        })
        alert(t('admin.accessProfileCreated'))
      }
      resetRoleDraft()
      await refreshWorkspaceRoles()
    } catch (err: any) {
      alert(err.response?.data?.detail || t('admin.accessProfileSaveFailed'))
    }
  }

  const handleEditWorkspaceRole = (role: WorkspaceCustomRole) => {
    setRoleDraft({
      id: role.id,
      name: role.name,
      description: role.description || '',
      base_role: role.base_role,
      permissions: normalizePermissions(role.permissions),
    })
  }

  const handleDeleteWorkspaceRole = async (roleId: string) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    if (!confirm(t('admin.deleteAccessProfileConfirm'))) return
    try {
      await axios.delete(`/access/workspace-roles/${roleId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (roleDraft.id === roleId) resetRoleDraft()
      await refreshWorkspaceRoles()
    } catch (err: any) {
      alert(err.response?.data?.detail || t('profile.updateFailed'))
    }
  }

  const handleUpdateCustomRole = async (userId: string, customRoleId: string) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    try {
      await axios.put(
        `/access/users/${userId}/custom-role`,
        { custom_role_id: customRoleId || null },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const res = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(res.data.map((user: any) => normalizeUser(user)))
    } catch (err: any) {
      alert(err.response?.data?.detail || t('admin.accessProfileUpdateFailed'))
    }
  }

  const handleUpdateRole = async (userId: string, newRole: string, departmentId?: string) => {
    const token = localStorage.getItem('crm_token')
    
    if (userId === currentUser?.id) {
      alert(t('admin.selfRoleBlocked'))
      return
    }
    
    if (roleMatches(newRole, ['MANAGER','USER']) && !departmentId) {
      alert(t('admin.selectDepartmentPlaceholder'))
      return
    }

    try {
      await axios.put(
        `/access/users/${userId}/role`,
        { new_role: newRole, department_id: departmentId || null },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      const res = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(res.data.map((user: any) => normalizeUser(user)))
      alert(t('admin.roleUpdated'))
    } catch (err: any) {
      alert(err.response?.data?.detail || t('admin.roleUpdateFailed'))
    }
  }

  const handleUpdateUserLanguage = async (userId: string, nextLanguage: AppLanguage) => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    try {
      await axios.put(
        `/access/users/${userId}`,
        { language: nextLanguage },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setUsers(prev => prev.map(user => (
        user.id === userId ? { ...user, language: nextLanguage } : user
      )))
    } catch (err: any) {
      alert(err.response?.data?.detail || t('profile.updateFailed'))
    }
  }

  const handleToggleUserStatus = async (userId: string) => {
    const token = localStorage.getItem('crm_token')
    
    const user = users.find(u => u.id === userId)
    if (!user) return
    if (user.id === currentUser?.id) {
      alert(t('admin.selfRoleBlocked'))
      return
    }

    try {
      const newStatus = !user.is_active
      
      await axios.put(
        `/access/users/${userId}`,
        { is_active: newStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      
      const res = await axios.get('/access/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(res.data.map((user: any) => normalizeUser(user)))
    } catch {
      alert(t('admin.statusUpdateFailed'))
    }
  }

  if (!currentUser || loading) return <div>{t('common.loading')}</div>

  // ✅ Filter users by selected tenant for non-superadmin
  const filteredUsers = roleMatches(currentUser.role, ['SUPERADMIN','SYSTEM_ADMIN'])
    ? users.filter(u => u.workspace_id === selectedWorkspace)
    : users

  const creationRoleOptions = getRoleOptionsForCreation(currentUser.role)

  return (
    <div className="crm-page-shell" style={{ padding: '20px' }}>

  {/* Back button */}
  <button
    onClick={() => navigate('/home')}
    style={{
      marginBottom: '15px',
      background: 'transparent',
      border: '1px solid #ccc',
      padding: '6px 12px',
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '13px',
      width: isMobile ? '100%' : 'auto'
    }}
  >
    ← {t('common.backHome')}
  </button>

  <h1>{t('admin.title')}</h1>

      
      {/* ✅ Tenant Selector for Superadmin */}
      {roleMatches(currentUser.role, ['SUPERADMIN','SYSTEM_ADMIN']) && workspaces.length > 0 && (
        <div style={{ marginBottom: '20px', padding: '10px', background: '#f0f0f0', borderRadius: '4px' }}>
          <label style={{ display: 'block' }}>
            <strong>{t('admin.selectWorkspace')}</strong>
            <select
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              style={{
                marginLeft: isMobile ? 0 : '10px',
                marginTop: isMobile ? '8px' : 0,
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                width: isMobile ? '100%' : 'auto'
              }}
            >
              {workspaces.map(workspace => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name} {!workspace.is_active && `(${t('common.inactive')})`}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={{
            padding: '10px 20px',
            background: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto'
          }}
        >
          {showCreateForm ? t('common.cancel') : t('admin.createNewUser')}
        </button>
      </div>

      {/* Create User Form */}
      {showCreateForm && (
        <form onSubmit={handleCreateUser} style={{
          padding: '20px',
          background: '#f9f9f9',
          border: '1px solid #ddd',
          borderRadius: '4px',
          marginBottom: '20px'
        }}>
          <div style={{ marginBottom: '15px' }}>
            <label>{t('admin.fullName')}</label>
            <input
              type="text"
              value={newUser.full_name}
              onChange={(e) => setNewUser({...newUser, full_name: e.target.value})}
              required
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label>{t('common.email')}:</label>
            <input
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({...newUser, email: e.target.value})}
              required
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label>{t('common.password')}:</label>
            <input
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser({...newUser, password: e.target.value})}
              required
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label>{t('admin.role')}</label>
            <select
              value={newUser.role}
              onChange={(e) => setNewUser({...newUser, role: e.target.value, department_id: ''})}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            >
              {creationRoleOptions.map(option => (
                <option key={option} value={option}>
                  {getRoleDisplayName(option)}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label>{t('admin.accessProfile')}</label>
            <select
              value={newUser.custom_role_id}
              onChange={(e) => setNewUser({...newUser, custom_role_id: e.target.value})}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            >
              <option value="">{t('admin.noAccessProfile')}</option>
              {workspaceRoles.map(role => (
                <option key={role.id} value={role.id}>
                  {role.name}
                </option>
              ))}
            </select>
          </div>

          {/* Workspace Selection */}
          <div style={{ marginBottom: '15px' }}>
            <label>{t('common.workspace')}:</label>
            <select
              value={newUser.workspace_id}
              onChange={(e) => setNewUser({...newUser, workspace_id: e.target.value})}
              required={!roleMatches(newUser.role, ['SUPERADMIN','SYSTEM_ADMIN'])}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            >
              <option value="">{t('admin.selectWorkspacePlaceholder')}</option>
              {(roleMatches(currentUser.role, ['SUPERADMIN','SYSTEM_ADMIN']) ? workspaces : workspaces.filter(w => w.id === currentUser.workspace_id)).map(workspace => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </div>

          {roleMatches(newUser.role, ['MANAGER','USER']) && (
            <div style={{ marginBottom: '15px' }}>
              <label>{t('common.department')}:</label>
              <select
                value={newUser.department_id}
                onChange={(e) => setNewUser({...newUser, department_id: e.target.value})}
                required
                style={{ width: '100%', padding: '8px', marginTop: '5px' }}
              >
                <option value="">{t('admin.selectDepartmentPlaceholder')}</option>
                {departments.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div style={{ marginBottom: '15px' }}>
            <label>{t('common.language')}:</label>
            <select
              value={newUser.language}
              onChange={(e) => setNewUser({...newUser, language: normalizeLanguage(e.target.value)})}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            >
              {LANGUAGE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            style={{
              padding: '10px 20px',
              background: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto'
            }}
          >
            {t('admin.createUser')}
          </button>
        </form>
      )}

      {/* Users List */}
      <h2>{t('common.users')} ({filteredUsers.length})</h2>
      {filteredUsers.length === 0 ? (
        <p>{t('admin.noUsers')}</p>
      ) : (
        <div className="crm-table-scroll">
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          marginTop: '20px'
        }}>
          <thead>
            <tr style={{ background: '#f0f0f0' }}>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.name')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.email')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.role')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('admin.accessProfile')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.language')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.department')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.status')}</th>
              <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'center' }}>{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map(user => (
              <tr key={user.id} style={{ opacity: user.is_active ? 1 : 0.5 }}>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>{user.full_name}</td>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>{user.email}</td>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                  <select
                    value={user.role}
                    onChange={(e) => handleUpdateRole(user.id, e.target.value, user.department_id || undefined)}
                    disabled={user.id === currentUser?.id}
                    style={{
                      opacity: user.id === currentUser?.id ? 0.5 : 1,
                      cursor: user.id === currentUser?.id ? 'not-allowed' : 'pointer',
                      padding: '4px'
                    }}
                  >
                    {resolveRoleOptions(user.role).map(option => (
                      <option key={option} value={option}>
                        {getRoleDisplayName(option)}
                      </option>
                    ))}
                  </select>
                </td>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                  <select
                    value={user.custom_role_id || ''}
                    onChange={(e) => handleUpdateCustomRole(user.id, e.target.value)}
                    disabled={user.id === currentUser?.id}
                    style={{
                      padding: '4px',
                      opacity: user.id === currentUser?.id ? 0.5 : 1,
                      cursor: user.id === currentUser?.id ? 'not-allowed' : 'pointer',
                    }}
                  >
                    <option value="">{t('admin.noAccessProfile')}</option>
                    {workspaceRoles.map(role => (
                      <option key={role.id} value={role.id}>
                        {role.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                  <select
                    value={user.language}
                    onChange={(e) => handleUpdateUserLanguage(user.id, normalizeLanguage(e.target.value))}
                    style={{ padding: '4px' }}
                  >
                    {LANGUAGE_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
                    ))}
                  </select>
                </td>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                  {roleMatches(user.role, ['MANAGER','USER']) ? (
                    <select
                      value={user.department_id || ''}
                      onChange={(e) => handleUpdateUserDepartment(user.id, e.target.value || null)}
                      style={{ padding: '6px', width: '100%' }}
                    >
                      <option value="">{t('admin.unassigned')}</option>
                      {departments.map(d => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span>—</span>
                  )}
                </td>
                <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                  {user.is_active ? t('common.active') : t('common.inactive')}
                </td>
                <td style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'center' }}>
                  <button
                    onClick={() => handleToggleUserStatus(user.id)}
                    disabled={user.id === currentUser?.id}
                    style={{
                      padding: '6px 12px',
                      background: user.is_active ? '#dc3545' : '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: user.id === currentUser?.id ? 'not-allowed' : 'pointer',
                      opacity: user.id === currentUser?.id ? 0.5 : 1,
                      fontSize: '12px'
                    }}
                  >
                    {user.is_active ? t('admin.deactivate') : t('admin.reactivate')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {/* Access Profiles */}
      <h2 style={{ marginTop: '40px' }}>{t('admin.accessProfiles')} ({workspaceRoles.length})</h2>
      <form onSubmit={handleSaveWorkspaceRole} style={{
        padding: '20px',
        background: '#f9f9f9',
        border: '1px solid #ddd',
        borderRadius: '4px',
        marginBottom: '20px'
      }}>
        <div className={isMobile ? 'crm-mobile-stack' : ''} style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 180px', gap: '12px' }}>
          <label>
            {t('admin.accessProfileName')}
            <input
              type="text"
              value={roleDraft.name}
              onChange={(e) => setRoleDraft(prev => ({ ...prev, name: e.target.value }))}
              placeholder={t('admin.accessProfileName')}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            />
          </label>
          <label>
            {t('common.description')}
            <input
              type="text"
              value={roleDraft.description}
              onChange={(e) => setRoleDraft(prev => ({ ...prev, description: e.target.value }))}
              placeholder={t('admin.descriptionOptional')}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            />
          </label>
          <label>
            {t('admin.baseRole')}
            <select
              value={roleDraft.base_role}
              onChange={(e) => setRoleDraft(prev => ({ ...prev, base_role: e.target.value }))}
              style={{ width: '100%', padding: '8px', marginTop: '5px' }}
            >
              {creationRoleOptions.map(option => (
                <option key={option} value={option}>
                  {getRoleDisplayName(option)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div style={{ marginTop: '18px' }}>
          <strong>{t('admin.tabVisibility')}</strong>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, minmax(160px, 1fr))', gap: '8px', marginTop: '10px' }}>
            {TAB_PERMISSION_OPTIONS.map(option => (
              <label key={option.key} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={roleDraft.permissions.tabs[option.key] !== false}
                  onChange={(e) => handleToggleTabPermission(option.key, e.target.checked)}
                />
                <span>{t(option.labelKey as any)}</span>
              </label>
            ))}
          </div>
        </div>

        <div style={{ marginTop: '18px' }}>
          <strong>{t('admin.fieldVisibility')}</strong>
          {formTemplates.length === 0 ? (
            <p style={{ color: '#666', marginTop: '8px' }}>{t('admin.noFormFields')}</p>
          ) : (
            <div style={{ display: 'grid', gap: '12px', marginTop: '10px' }}>
              {formTemplates.map(template => (
                <div key={template.id} style={{ border: '1px solid #e0e0e0', borderRadius: '6px', padding: '10px', background: '#fff' }}>
                  <div style={{ fontWeight: 700, marginBottom: '8px' }}>{template.name}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, minmax(180px, 1fr))', gap: '8px' }}>
                    {(template.schema_structure || []).map(field => {
                      const visibilityKey = formFieldVisibilityKey(template.id, field.key)
                      return (
                        <label key={`${template.id}-${field.key}`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input
                            type="checkbox"
                            checked={roleDraft.permissions.fields.forms?.[visibilityKey] !== false}
                            onChange={(e) => handleToggleFieldPermission(template.id, field.key, e.target.checked)}
                          />
                          <span>{field.label || field.key}</span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', marginTop: '18px', flexWrap: 'wrap' }}>
          <button type="submit" style={{ padding: '10px 18px', background: '#111', color: '#fff', border: 0, borderRadius: '4px', cursor: 'pointer' }}>
            {roleDraft.id ? t('admin.saveAccessProfile') : t('admin.createAccessProfile')}
          </button>
          {roleDraft.id && (
            <button type="button" onClick={resetRoleDraft} style={{ padding: '10px 18px', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}>
              {t('common.cancel')}
            </button>
          )}
        </div>
      </form>

      {workspaceRoles.length > 0 && (
        <div className="crm-table-scroll">
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px' }}>
            <thead>
              <tr style={{ background: '#f0f0f0' }}>
                <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('admin.accessProfile')}</th>
                <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('admin.baseRole')}</th>
                <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left' }}>{t('common.description')}</th>
                <th style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'center' }}>{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {workspaceRoles.map(role => (
                <tr key={role.id}>
                  <td style={{ border: '1px solid #ddd', padding: '10px' }}>{role.name}</td>
                  <td style={{ border: '1px solid #ddd', padding: '10px' }}>{getRoleDisplayName(role.base_role)}</td>
                  <td style={{ border: '1px solid #ddd', padding: '10px' }}>{role.description || '—'}</td>
                  <td style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'center' }}>
                    <button type="button" onClick={() => handleEditWorkspaceRole(role)} style={{ marginRight: '8px' }}>
                      {t('common.edit')}
                    </button>
                    <button type="button" onClick={() => handleDeleteWorkspaceRole(role.id)}>
                      {t('common.delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Departments Management */}
      <h2 style={{ marginTop: '40px' }}>{t('admin.departments')} ({departments.length})</h2>
      <form onSubmit={handleCreateDepartment} className={isMobile ? 'crm-mobile-stack' : ''} style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
        <input
          placeholder={t('admin.departmentName')}
          value={newDept.name}
          onChange={(e) => setNewDept({ ...newDept, name: e.target.value })}
          required
          style={{ padding: '8px', flex: 1, width: isMobile ? '100%' : undefined }}
        />
        <input
          placeholder={t('admin.descriptionOptional')}
          value={newDept.description}
          onChange={(e) => setNewDept({ ...newDept, description: e.target.value })}
          style={{ padding: '8px', flex: 2, width: isMobile ? '100%' : undefined }}
        />
        <button type="submit" style={{ padding: '8px 14px', width: isMobile ? '100%' : 'auto' }}>{t('admin.add')}</button>
      </form>

      {departments.length === 0 ? (
        <p>{t('admin.noDepartments')}</p>
      ) : (
        <div className="crm-table-scroll">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f0f0f0' }}>
              <th style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>{t('common.name')}</th>
              <th style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>{t('common.description')}</th>
              <th style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {departments.map(d => (
              <tr key={d.id}>
                <td style={{ border: '1px solid #ddd', padding: '8px' }}>
                  {editDeptId === d.id ? (
                    <input
                      value={editDeptName}
                      onChange={(e) => setEditDeptName(e.target.value)}
                      style={{ width: '100%', padding: '6px' }}
                    />
                  ) : (
                    d.name
                  )}
                </td>
                <td style={{ border: '1px solid #ddd', padding: '8px' }}>
                  {editDeptId === d.id ? (
                    <input
                      value={editDeptDescription}
                      onChange={(e) => setEditDeptDescription(e.target.value)}
                      style={{ width: '100%', padding: '6px' }}
                    />
                  ) : (
                    d.description || '—'
                  )}
                </td>
                <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                  {editDeptId === d.id ? (
                    <>
                      <button
                        onClick={() => handleUpdateDepartment(d.id)}
                        style={{ marginRight: '8px' }}
                      >
                        {t('common.save')}
                      </button>
                      <button onClick={() => setEditDeptId(null)}>{t('common.cancel')}</button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setEditDeptId(d.id)
                          setEditDeptName(d.name)
                          setEditDeptDescription(d.description || '')
                        }}
                        style={{ marginRight: '8px' }}
                      >
                        {t('common.edit')}
                      </button>
                      <button onClick={() => handleDeleteDepartment(d.id)}>{t('common.delete')}</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  )
}

export default AdminPage
