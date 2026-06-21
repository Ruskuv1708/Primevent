import { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { normalizeRole, roleMatches } from '../shared/roleLabels'
import { getWorkspaceParams } from '../shared/workspace'
import type { RequestItem } from '../features/requests/types'
import useIsMobile from '../shared/useIsMobile'
import {
  isModuleEnabled,
} from '../shared/modules'
import { getMarketShell } from '../shared/marketShell'
import { useI18n } from '../shared/i18nContext'
import { LANGUAGE_OPTIONS, normalizeLanguage } from '../shared/language'
import { canViewTab } from '../shared/roleVisibility'

const normalizeUserRole = (user: any) => ({
  ...user,
  role: normalizeRole(user.role)
})

type NotificationStats = {
  assigned: number
  pending: number
  newCount: number
}

type MenuIconName =
  | 'brand'
  | 'dashboard'
  | 'requests'
  | 'assigned'
  | 'history'
  | 'schedule'
  | 'evaluations'
  | 'departments'
  | 'registry'
  | 'reports'
  | 'report_types'
  | 'forms'
  | 'modules'
  | 'profile'
  | 'admin'
  | 'superadmin'

type MenuItem = {
  label: string
  path: string
  icon: MenuIconName
  tabKey: string
}

const menuItem = (label: string, path: string, icon: MenuIconName, tabKey: string): MenuItem => ({
  label,
  path,
  icon,
  tabKey,
})

const isMenuPathActive = (path: string, pathname: string) => {
  if (path === '/requests') {
    return pathname === '/requests' || /^\/requests\/(?!assigned(?:\/|$)|history(?:\/|$)).+/.test(pathname)
  }
  if (path === '/forms') {
    return pathname === '/forms' || /^\/forms\/(?!new(?:\/|$)).+/.test(pathname)
  }
  return pathname === path || pathname.startsWith(`${path}/`)
}

const getInitials = (name?: string) => {
  if (!name) return 'U'
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase())
    .join('') || 'U'
}

const SidebarIcon = ({ name, size = 16 }: { name: MenuIconName; size?: number }) => {
  const baseProps = {
    width: size,
    height: size,
    viewBox: '0 0 20 20',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className: 'crm-nav-icon',
    'aria-hidden': true as const,
  }

  switch (name) {
    case 'brand':
      return (
        <svg {...baseProps}>
          <rect x="3" y="3" width="14" height="14" rx="3" />
          <path d="M7 7h6M7 10h6M7 13h3" />
        </svg>
      )
    case 'dashboard':
      return (
        <svg {...baseProps}>
          <path d="M3 9.5 10 4l7 5.5V17a1 1 0 0 1-1 1h-4v-5H8v5H4a1 1 0 0 1-1-1z" />
        </svg>
      )
    case 'requests':
      return (
        <svg {...baseProps}>
          <rect x="4" y="3" width="12" height="14" rx="2" />
          <path d="M7 7h6M7 10h6M7 13h4" />
        </svg>
      )
    case 'assigned':
      return (
        <svg {...baseProps}>
          <circle cx="10" cy="10" r="7" />
          <path d="m7 10 2 2 4-4" />
        </svg>
      )
    case 'history':
      return (
        <svg {...baseProps}>
          <path d="M4 9a6 6 0 1 1 1.8 4.3" />
          <path d="M4 5v4h4M10 6.8V10l2.2 1.4" />
        </svg>
      )
    case 'schedule':
      return (
        <svg {...baseProps}>
          <rect x="3" y="4" width="14" height="13" rx="2" />
          <path d="M7 2.8v3M13 2.8v3M3 8h14M7 11h2M11 11h2M7 14h2" />
        </svg>
      )
    case 'evaluations':
      return (
        <svg {...baseProps}>
          <path d="M5 4h10a1 1 0 0 1 1 1v12H4V5a1 1 0 0 1 1-1z" />
          <path d="M7 8h6M7 11h3" />
          <path d="m11.5 14 1.2 1.2 2.3-2.7" />
        </svg>
      )
    case 'departments':
      return (
        <svg {...baseProps}>
          <circle cx="7" cy="7" r="2.2" />
          <circle cx="13" cy="7" r="2.2" />
          <path d="M3.8 15c.6-2.2 2.1-3.5 3.9-3.5S11 12.8 11.6 15M8.4 15c.6-1.8 2-3 3.6-3s3 1.2 3.6 3" />
        </svg>
      )
    case 'registry':
      return (
        <svg {...baseProps}>
          <rect x="3" y="4" width="14" height="12" rx="2" />
          <path d="M3 8h14M7 12h6M7 15h4" />
        </svg>
      )
    case 'reports':
      return (
        <svg {...baseProps}>
          <path d="M4 16V9M10 16V6M16 16V11M3 16h14" />
        </svg>
      )
    case 'report_types':
      return (
        <svg {...baseProps}>
          <rect x="3" y="4" width="14" height="12" rx="1.5" />
          <path d="M3 8h14M8 8v8M13 8v8" />
        </svg>
      )
    case 'forms':
      return (
        <svg {...baseProps}>
          <path d="M6 3h6l3 3v11a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
          <path d="M12 3v4h4M8 11h4M8 14h4" />
        </svg>
      )
    case 'modules':
      return (
        <svg {...baseProps}>
          <rect x="3" y="3" width="5" height="5" rx="1.2" />
          <rect x="12" y="3" width="5" height="5" rx="1.2" />
          <rect x="3" y="12" width="5" height="5" rx="1.2" />
          <rect x="12" y="12" width="5" height="5" rx="1.2" />
        </svg>
      )
    case 'profile':
      return (
        <svg {...baseProps}>
          <circle cx="10" cy="7" r="3" />
          <path d="M4.5 17c.9-3 2.8-4.5 5.5-4.5s4.6 1.5 5.5 4.5" />
        </svg>
      )
    case 'admin':
      return (
        <svg {...baseProps}>
          <path d="M10 3 16 6v4c0 3.8-2.3 6-6 7-3.7-1-6-3.2-6-7V6z" />
          <path d="m7.2 10 1.7 1.8 3-3.2" />
        </svg>
      )
    case 'superadmin':
      return (
        <svg {...baseProps}>
          <path d="m10 3 2.1 4.2 4.6.7-3.3 3.2.8 4.6L10 13.6l-4.2 2.1.8-4.6L3.3 7.9l4.6-.7z" />
        </svg>
      )
    default:
      return null
  }
}

function AppLayout() {
  const { language, setLanguage, t } = useI18n()
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [notificationsLoading, setNotificationsLoading] = useState(false)
  const [notificationStats, setNotificationStats] = useState<NotificationStats>({
    assigned: 0,
    pending: 0,
    newCount: 0,
  })
  const [enabledModules, setEnabledModules] = useState<string[]>([])
  const [modulesLoaded, setModulesLoaded] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const notificationsEnabled = isModuleEnabled(enabledModules, 'notifications')
  const workflowEnabled = isModuleEnabled(enabledModules, 'workflow')
  const notificationStatsEnabled = notificationsEnabled && workflowEnabled

  const loadEnabledModules = async (user: any, token: string) => {
    setModulesLoaded(false)
    const workspaceParams = getWorkspaceParams(user)
    const hasWorkspaceScope = Boolean(user?.workspace_id || workspaceParams?.workspace_id)
    if (!hasWorkspaceScope) {
      setEnabledModules([])
      setModulesLoaded(true)
      return []
    }
    try {
      const currentRes = await axios.get('/modules/current', {
        headers: { Authorization: `Bearer ${token}` },
        params: workspaceParams,
      })
      const nextModules = Array.isArray(currentRes.data?.enabled_modules)
        ? currentRes.data.enabled_modules
        : []
      setEnabledModules(nextModules)
      return nextModules
    } catch (err) {
      console.warn('Failed to load workspace modules', err)
      setEnabledModules([])
      return []
    } finally {
      setModulesLoaded(true)
    }
  }

  const loadNotificationStats = async (user: any, modules: string[] = enabledModules) => {
    const token = localStorage.getItem('crm_token')
    if (!token || !user?.id) return
    if (!isModuleEnabled(modules, 'notifications') || !isModuleEnabled(modules, 'workflow')) {
      setNotificationStats({ assigned: 0, newCount: 0, pending: 0 })
      setNotificationsLoading(false)
      return
    }
    setNotificationsLoading(true)
    try {
      const params = {
        ...(getWorkspaceParams(user) || {}),
        assignee_id: user.id,
      }
      const res = await axios.get('/workflow/requests', {
        headers: { Authorization: `Bearer ${token}` },
        params,
      })
      const assignedRequests: RequestItem[] = Array.isArray(res.data) ? res.data : []
      const ownAssigned = assignedRequests.filter(req => {
        return typeof req?.assigned_to_id === 'string' && req.assigned_to_id.toLowerCase() === String(user.id).toLowerCase()
      })
      setNotificationStats({
        assigned: ownAssigned.length,
        newCount: ownAssigned.filter(req => req.status === 'new').length,
        pending: ownAssigned.filter(req => req.status === 'pending').length,
      })
    } catch (err) {
      console.warn('Failed to load request notifications', err)
      setNotificationStats({ assigned: 0, newCount: 0, pending: 0 })
    } finally {
      setNotificationsLoading(false)
    }
  }

  useEffect(() => {
    let isMounted = true

    ;(async () => {
      const token = localStorage.getItem('crm_token')
      if (!token) {
        navigate('/')
        return
      }
      try {
        const res = await axios.get('/access/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const normalized = normalizeUserRole(res.data)
        if (!isMounted) return
        setLanguage(normalizeLanguage(normalized.language))
        setCurrentUser(normalized)
        void loadEnabledModules(normalized, token)
      } catch {
        localStorage.removeItem('crm_token')
        navigate('/')
      }
    })()

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (!currentUser || !modulesLoaded) return
    if (!notificationStatsEnabled) {
      setNotificationStats({ assigned: 0, newCount: 0, pending: 0 })
      return
    }
    loadNotificationStats(currentUser)
    const intervalId = window.setInterval(() => {
      loadNotificationStats(currentUser)
    }, 30000)
    return () => window.clearInterval(intervalId)
  }, [currentUser?.id, modulesLoaded, notificationStatsEnabled])

  useEffect(() => {
    if (!currentUser) return
    const handleModuleUpdate = (event: Event) => {
      const detail = (event as CustomEvent<{
        workspaceId?: string
        enabledModules?: string[]
      }>).detail
      const workspaceParams = getWorkspaceParams(currentUser)
      const activeWorkspaceId = currentUser.workspace_id || workspaceParams?.workspace_id
      if (detail?.workspaceId && detail.workspaceId !== activeWorkspaceId) return
      if (Array.isArray(detail?.enabledModules)) setEnabledModules(detail.enabledModules)
      setModulesLoaded(true)
    }
    window.addEventListener('crm:workspace-modules-updated', handleModuleUpdate)
    return () => window.removeEventListener('crm:workspace-modules-updated', handleModuleUpdate)
  }, [currentUser])

  useEffect(() => {
    setSidebarOpen(!isMobile)
  }, [isMobile])

  useEffect(() => {
    if (!isMobile) return
    setSidebarOpen(false)
  }, [location.pathname, isMobile])

  useEffect(() => {
    document.documentElement.dataset.theme = 'light'
    document.body.classList.remove('crm-ui-mode-1c')
    document.body.classList.add('crm-ui-mode-cards')
  }, [])

  const menuItems = useMemo<MenuItem[]>(() => {
    if (!currentUser) return []
    const marketShell = getMarketShell()
    const isAdmin = roleMatches(currentUser.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])
    const isManager = roleMatches(currentUser.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN', 'MANAGER'])
    const items = [
      ...(isModuleEnabled(enabledModules, 'workspace_home')
        ? [menuItem(t('nav.home') || marketShell.sections.home, '/home', 'dashboard', 'home')]
        : []),
      ...(isModuleEnabled(enabledModules, 'dashboard')
        ? [menuItem(t('nav.dashboard'), '/dashboard', 'dashboard', 'home')]
        : []),
      ...(isModuleEnabled(enabledModules, 'registry')
        ? [menuItem(t('nav.people') || marketShell.sections.people, '/registry', 'registry', 'people')]
        : []),
      ...(isModuleEnabled(enabledModules, 'open_requests')
        ? [menuItem(t('market.openRequests'), '/requests', 'requests', 'work')]
        : []),
      ...(isModuleEnabled(enabledModules, 'assigned_work')
        ? [menuItem(t('market.openAssignedWork'), '/requests/assigned', 'assigned', 'work')]
        : []),
      ...(isModuleEnabled(enabledModules, 'request_history')
        ? [menuItem(t('nav.requestHistory'), '/requests/history', 'history', 'work')]
        : []),
      ...(isModuleEnabled(enabledModules, 'departments') && isManager
        ? [menuItem(t('market.departments'), '/departments', 'departments', 'work')]
        : []),
      ...(isModuleEnabled(enabledModules, 'animator_schedule')
        ? [menuItem(t('nav.schedule'), '/animator-schedule', 'schedule', 'animator_schedule')]
        : []),
      ...(isModuleEnabled(enabledModules, 'employee_evaluations')
        ? [menuItem(t('nav.employeeEvaluations'), '/employee-evaluations', 'evaluations', 'employee_evaluations')]
        : []),
      ...(isModuleEnabled(enabledModules, 'form_templates')
        ? [menuItem(t('market.openForms'), '/forms', 'forms', 'money')]
        : []),
      ...(isModuleEnabled(enabledModules, 'form_builder') && isManager
        ? [menuItem(t('nav.newTemplate'), '/forms/new', 'forms', 'money')]
        : []),
      ...(isModuleEnabled(enabledModules, 'report_library')
        ? [menuItem(t('market.openReports'), '/reports', 'reports', 'reports')]
        : []),
      ...(isModuleEnabled(enabledModules, 'report_types') && isAdmin
        ? [menuItem(t('market.reportTypes'), '/report-types', 'report_types', 'reports')]
        : []),
    ]
    return items.filter(item => canViewTab(currentUser, item.tabKey))
  }, [currentUser, enabledModules, t])

  const toolbarTitle = useMemo(() => {
    const activeItem = menuItems.find(item => isMenuPathActive(item.path, location.pathname))
    return activeItem?.label || t('nav.workspace')
  }, [location.pathname, menuItems, t])

  if (!currentUser) {
    return <div className="crm-loading-state">{t('common.loading')}</div>
  }

  const userRole = String(currentUser.role || 'USER').toUpperCase()
  const assignedLabel = notificationsLoading ? '...' : String(notificationStats.assigned)
  const shellClass = `crm-app-shell ${sidebarOpen ? 'is-sidebar-open' : 'is-sidebar-closed'}`

  return (
    <div className={shellClass}>
      {isMobile && sidebarOpen && (
        <button
          className="crm-sidebar-backdrop"
          type="button"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close menu"
        />
      )}

      <aside className="crm-sidebar" aria-label="Workspace navigation">
        <div className="crm-workspace">
          <div className="crm-workspace-mark">P</div>
          <div className="crm-workspace-text">
            <span className="crm-workspace-name">Prime Event CRM</span>
            <span className="crm-workspace-role">CRM</span>
          </div>
        </div>

        <div className="crm-sidebar-section">{t('nav.workspace')}</div>
        <nav className="crm-nav">
          {menuItems.map(item => {
            const active = isMenuPathActive(item.path, location.pathname)
            const showBadge = notificationStatsEnabled && item.path === '/requests/assigned' && notificationStats.assigned > 0

            return (
              <button
                key={item.path}
                type="button"
                title={item.label}
                className={active ? 'crm-nav-item is-active' : 'crm-nav-item'}
                onClick={() => {
                  navigate(item.path)
                  if (isMobile) setSidebarOpen(false)
                }}
              >
                <SidebarIcon name={item.icon} />
                <span className="crm-nav-label">{item.label}</span>
                {showBadge && <span className="crm-nav-badge">{assignedLabel}</span>}
              </button>
            )
          })}
          {isModuleEnabled(enabledModules, 'profile') && canViewTab(currentUser, 'settings') && (
            <button
              type="button"
              className={location.pathname.startsWith('/profile') ? 'crm-nav-item is-active' : 'crm-nav-item'}
              onClick={() => navigate('/profile')}
            >
              <SidebarIcon name="profile" />
              <span className="crm-nav-label">{t('nav.profile')}</span>
            </button>
          )}
          {isModuleEnabled(enabledModules, 'ai_architect') && canViewTab(currentUser, 'ai_architect') && (
            <button
              type="button"
              className={location.pathname.startsWith('/ai-architect') ? 'crm-nav-item is-active' : 'crm-nav-item'}
              onClick={() => navigate('/ai-architect')}
            >
              <SidebarIcon name="modules" />
              <span className="crm-nav-label">{t('nav.aiArchitect')}</span>
            </button>
          )}
          {isModuleEnabled(enabledModules, 'admin_panel') && userRole.includes('ADMIN') && canViewTab(currentUser, 'admin') && (
            <button
              type="button"
              className={location.pathname.startsWith('/admin') ? 'crm-nav-item is-active' : 'crm-nav-item'}
              onClick={() => navigate('/admin')}
            >
              <SidebarIcon name="admin" />
              <span className="crm-nav-label">{t('nav.admin')}</span>
            </button>
          )}
          {isModuleEnabled(enabledModules, 'superadmin_panel') && userRole.includes('SUPER') && canViewTab(currentUser, 'superadmin') && (
            <button
              type="button"
              className={location.pathname.startsWith('/superadmin') ? 'crm-nav-item is-active' : 'crm-nav-item'}
              onClick={() => navigate('/superadmin')}
            >
              <SidebarIcon name="superadmin" />
              <span className="crm-nav-label">{t('nav.superadmin')}</span>
            </button>
          )}
        </nav>

        <div className="crm-sidebar-footer">
          {isModuleEnabled(enabledModules, 'profile') ? (
            <button type="button" className="crm-profile-chip" onClick={() => navigate('/profile')}>
              <span className="crm-avatar">{getInitials(currentUser.full_name)}</span>
              <span className="crm-profile-meta">
                <span className="crm-profile-name">{currentUser.full_name}</span>
                {notificationStatsEnabled && (
                  <span className="crm-profile-stats">
                    {notificationStats.newCount} {t('nav.newPending').split(' / ')[0]} / {notificationStats.pending} {t('nav.newPending').split(' / ')[1]}
                  </span>
                )}
              </span>
            </button>
          ) : (
            <div className="crm-profile-chip" aria-label={currentUser.full_name}>
              <span className="crm-avatar">{getInitials(currentUser.full_name)}</span>
              <span className="crm-profile-meta">
                <span className="crm-profile-name">{currentUser.full_name}</span>
              </span>
            </div>
          )}
        </div>
      </aside>

      <div className="crm-main">
        <header className="crm-toolbar">
          <div className="crm-toolbar-left">
            <button
              type="button"
              className="btn btn--secondary btn--sm crm-menu-button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <svg className="btn-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                <path d="M4 6h12M4 10h12M4 14h12" />
              </svg>
            </button>
            <span className="crm-toolbar-title">{toolbarTitle}</span>
            <span className="crm-toolbar-subtitle">{userRole}</span>
          </div>
          <div className="crm-toolbar-spacer" />
          <div className="crm-command" aria-hidden="true">
            {t('nav.searchWorkspace')}
            <kbd>⌘K</kbd>
          </div>
          <div className="crm-toolbar-actions">
            <div className="crm-language-switch crm-language-switch--compact" role="group" aria-label={t('common.language')}>
              {LANGUAGE_OPTIONS.map(option => (
                <button
                  key={option.value}
                  type="button"
                  className={language === option.value ? 'is-active' : ''}
                  onClick={() => setLanguage(option.value)}
                >
                  {option.value.toUpperCase()}
                </button>
              ))}
            </div>
            {isModuleEnabled(enabledModules, 'assigned_work') && canViewTab(currentUser, 'work') && (
              <button type="button" className="btn btn--secondary btn--sm" onClick={() => navigate('/requests/assigned')}>
                {t('nav.assigned')}: {assignedLabel}
              </button>
            )}
            {isModuleEnabled(enabledModules, 'profile') && (
              <button type="button" className="btn btn--primary btn--sm" onClick={() => navigate('/profile')}>
                {t('nav.profile')}
              </button>
            )}
          </div>
        </header>

        <main className="crm-content">
          <Outlet context={{ currentUser, enabledModules, modulesLoaded }} />
        </main>
      </div>
    </div>
  )
}

export default AppLayout
