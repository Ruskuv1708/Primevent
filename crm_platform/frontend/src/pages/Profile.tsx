import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import useIsMobile from '../shared/useIsMobile'
import { useI18n } from '../shared/i18nContext'
import { LANGUAGE_OPTIONS, normalizeLanguage } from '../shared/language'
import theme from '../shared/theme'

const normalizeRole = (value?: string) => (value || '').toUpperCase()

function Profile() {
  const { language, setLanguage, t } = useI18n()
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [tenant, setTenant] = useState<any>(null)
  const [department, setDepartment] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    language,
  })
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  useEffect(() => {
    const token = localStorage.getItem('crm_token')
    if (!token) {
      navigate('/')
      return
    }

    const loadProfile = async () => {
      try {
        const res = await axios.get('/access/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const user = {
          ...res.data,
          role: normalizeRole(res.data.role),
          language: normalizeLanguage(res.data.language),
        }
        setLanguage(user.language)
        setCurrentUser(user)
        setFormData({
          full_name: user.full_name,
          email: user.email,
          language: user.language,
        })

        if (user.workspace_id) {
          const tenantRes = await axios.get(
            `/superadmin/workspaces/${user.workspace_id}`,
            { headers: { Authorization: `Bearer ${token}` } }
          )
          setTenant(tenantRes.data)
        }

        if (user.department_id) {
          const params = user.workspace_id ? { workspace_id: user.workspace_id } : undefined
          const deptRes = await axios.get('/workflow/departments', {
            headers: { Authorization: `Bearer ${token}` },
            params
          })
          const activeDept = deptRes.data.find((dept: any) => dept.id.toLowerCase() === user.department_id.toLowerCase())
          setDepartment(activeDept || null)
        }
        setLoading(false)
      } catch (err) {
        console.error('Error:', err)
        setLoading(false)
      }
    }

    loadProfile()
  }, [navigate])

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem('crm_token')

    try {
      await axios.put(
        '/access/me',
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setLanguage(normalizeLanguage(formData.language))
      setCurrentUser((prev: any) => prev ? { ...prev, ...formData } : prev)
      alert(t('profile.updated'))
      setEditMode(false)
    } catch (err: any) {
      alert(err.response?.data?.detail || t('profile.updateFailed'))
    }
  }

  if (loading) return <div style={{ padding: theme.spacing.xxl }}>{t('common.loading')}</div>
  if (!currentUser) return <div style={{ padding: theme.spacing.xxl }}>{t('common.user')}?</div>

  const getRoleColor = (role: string) => {
    const roleUpper = role?.toUpperCase() || ''
    switch (roleUpper) {
      case 'SUPERADMIN': return theme.colors.roles.superadmin
      case 'ADMIN': return theme.colors.roles.admin
      case 'MANAGER': return theme.colors.roles.manager
      case 'USER': return theme.colors.roles.user
      case 'VIEWER': return theme.colors.roles.viewer
      default: return theme.colors.gray.text
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('crm_token')
    navigate('/')
  }

  return (
    <div className="crm-page-shell" style={{ padding: theme.spacing.xxl, maxWidth: '600px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: theme.spacing.sm }}>
        <h1>{t('profile.title')}</h1>
        <button
          onClick={handleLogout}
          style={{
            padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
            background: theme.colors.white,
            color: theme.colors.error,
            border: `1px solid ${theme.colors.error}`,
            borderRadius: theme.borderRadius.sm,
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: '500'
          }}
        >
          {t('profile.logout')}
        </button>
      </div>

      {/* User Information Card */}
      <div style={{
        padding: theme.spacing.xxl,
        background: theme.colors.gray.light,
        border: `1px solid ${theme.colors.gray.border}`,
        borderRadius: theme.borderRadius.lg,
        marginBottom: theme.spacing.xxl
      }}>
        {/* ✅ Role Badge */}
        <div style={{ marginBottom: theme.spacing.lg }}>
          <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('profile.role')}</label>
          <div style={{
            display: 'inline-block',
            background: getRoleColor(currentUser?.role),
            color: theme.colors.white,
            padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
            borderRadius: theme.borderRadius.sm,
            fontWeight: '600',
            marginTop: theme.spacing.sm,
            fontSize: '13px'
          }}>
            {currentUser?.role?.toUpperCase() || 'N/A'}
          </div>
        </div>

        {/* ✅ Workspace/Tenant Information */}
            <div style={{ marginBottom: theme.spacing.lg, paddingBottom: theme.spacing.lg, borderBottom: `1px solid ${theme.colors.gray.border}` }}>
              <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('profile.workspaceInfo')}</label>
          <div style={{ marginTop: theme.spacing.sm, fontSize: '13px' }}>
            {tenant ? (
              <div>
                <strong>{tenant.name}</strong>
                <div style={{ color: theme.colors.gray.text, fontSize: '12px', marginTop: '3px' }}>
                  ID: {currentUser?.workspace_id}
                </div>
                <div style={{
                  marginTop: theme.spacing.sm,
                  display: 'inline-block',
                  background: tenant.is_active ? theme.colors.success : theme.colors.error,
                  color: theme.colors.white,
                  padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                  borderRadius: theme.borderRadius.sm,
                  fontSize: '12px'
                }}>
                  {tenant.is_active ? t('common.active') : t('common.inactive')}
                </div>
              </div>
            ) : (
              <span style={{ color: theme.colors.gray.text }}>{t('profile.loadingWorkspace')}</span>
            )}
          </div>
        </div>

        {department && (
          <div style={{ marginBottom: theme.spacing.lg }}>
            <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('profile.department')}</label>
            <div style={{ marginTop: theme.spacing.sm, fontSize: '13px' }}>
              <strong>{department.name}</strong>
              <div style={{ color: theme.colors.gray.text, fontSize: '12px', marginTop: '3px' }}>
                ID: {department.id}
              </div>
            </div>
          </div>
        )}

        {/* Full Name */}
        <div style={{ marginBottom: theme.spacing.lg }}>
          <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('profile.fullName')}</label>
          <p style={{ margin: `${theme.spacing.xs} 0`, fontSize: '13px' }}>
            {!editMode ? (
              currentUser?.full_name
            ) : (
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                style={{ width: '100%', padding: theme.spacing.sm, borderRadius: theme.borderRadius.sm, border: `1px solid ${theme.colors.gray.border}` }}
              />
            )}
          </p>
        </div>

        {/* Email */}
        <div style={{ marginBottom: theme.spacing.lg }}>
          <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('common.email')}</label>
          <p style={{ margin: `${theme.spacing.xs} 0`, fontSize: '13px' }}>
            {!editMode ? (
              currentUser?.email
            ) : (
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                style={{ width: '100%', padding: theme.spacing.sm, borderRadius: theme.borderRadius.sm, border: `1px solid ${theme.colors.gray.border}` }}
              />
            )}
          </p>
        </div>

        <div style={{ marginBottom: theme.spacing.lg }}>
          <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('common.language')}</label>
          <p style={{ margin: `${theme.spacing.xs} 0`, fontSize: '13px' }}>
            {!editMode ? (
              LANGUAGE_OPTIONS.find(option => option.value === currentUser?.language)?.labelKey
                ? t(LANGUAGE_OPTIONS.find(option => option.value === currentUser?.language)!.labelKey)
                : t('common.russian')
            ) : (
              <select
                value={formData.language}
                onChange={(e) => setFormData({...formData, language: normalizeLanguage(e.target.value)})}
                style={{ width: '100%', padding: theme.spacing.sm, borderRadius: theme.borderRadius.sm, border: `1px solid ${theme.colors.gray.border}` }}
              >
                {LANGUAGE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
                ))}
              </select>
            )}
          </p>
        </div>

        {/* Status */}
        <div style={{ marginBottom: theme.spacing.lg }}>
          <label style={{ fontSize: '12px', color: theme.colors.gray.text }}>{t('profile.accountStatus')}</label>
          <div style={{
            marginTop: theme.spacing.sm,
            display: 'inline-block',
            background: currentUser?.is_active ? theme.colors.success : theme.colors.error,
            color: theme.colors.white,
            padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
            borderRadius: theme.borderRadius.sm,
            fontSize: '12px'
          }}>
            {currentUser?.is_active ? t('common.active') : t('common.inactive')}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className={isMobile ? 'crm-mobile-stack' : ''} style={{ display: 'flex', gap: theme.spacing.sm, flexWrap: 'wrap' }}>
        {!editMode ? (
          <button
            onClick={() => setEditMode(true)}
            style={{
              padding: `${theme.spacing.lg} ${theme.spacing.xxl}`,
              background: theme.colors.info,
              color: theme.colors.white,
              border: 'none',
              borderRadius: theme.borderRadius.sm,
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto'
            }}
          >
            {t('profile.editProfile')}
          </button>
        ) : (
          <>
            <button
              onClick={handleUpdateProfile}
              style={{
                padding: `${theme.spacing.lg} ${theme.spacing.xxl}`,
                background: theme.colors.success,
                color: theme.colors.white,
                border: 'none',
                borderRadius: theme.borderRadius.sm,
                cursor: 'pointer',
                width: isMobile ? '100%' : 'auto'
              }}
            >
              {t('profile.saveChanges')}
            </button>
            <button
              onClick={() => setEditMode(false)}
              style={{
                padding: `${theme.spacing.lg} ${theme.spacing.xxl}`,
                background: theme.colors.gray.textLight,
                color: theme.colors.white,
                border: 'none',
                borderRadius: theme.borderRadius.sm,
                cursor: 'pointer',
                width: isMobile ? '100%' : 'auto'
              }}
            >
              {t('common.cancel')}
            </button>
          </>
        )}

        <button
          onClick={() => navigate('/home')}
          style={{
            padding: `${theme.spacing.lg} ${theme.spacing.xxl}`,
            background: theme.colors.gray.disabled,
            color: theme.colors.white,
            border: 'none',
            borderRadius: theme.borderRadius.sm,
            cursor: 'pointer',
            marginLeft: isMobile ? 0 : 'auto',
            width: isMobile ? '100%' : 'auto'
          }}
        >
          ← {t('common.backHome')}
        </button>
      </div>
    </div>
  )
}

export default Profile
