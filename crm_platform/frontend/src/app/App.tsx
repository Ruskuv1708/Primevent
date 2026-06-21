import { BrowserRouter, Navigate, Routes, Route } from 'react-router-dom'
import type { ReactElement } from 'react'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Profile from '../pages/Profile'
import RequestsPage from '../features/requests/RequestsPage'
import AssignedRequestsPage from '../features/requests/AssignedRequestsPage'
import DepartmentsPage from '../features/requests/DepartmentsPage'
import RequestsHistoryPage from '../features/requests/RequestsHistoryPage'
import TemplatesPage from '../features/forms/TemplatesPage'
import FormFillPage from '../features/forms/FormFillPage'
import FormRecordsPage from '../features/forms/FormRecordsPage'
import FormQueuePage from '../features/forms/FormQueuePage'
import TemplateBuilderPage from '../features/forms/TemplateBuilderPage'
import AdminPage from '../features/admin/AdminPage'
import WorkspaceManagementPage from '../features/workspaces/WorkspaceManagementPage'
import RequestDetailsPage from '../features/requests/RequestDetailsPage'
import AppLayout from '../layouts/AppLayout'
import FilesPage from '../features/files/FilesPage'
import ReportsPage from '../features/reports/ReportsPage'
import ReportTypesPage from '../features/reports/ReportTypesPage'
import RegistryPage from '../features/registry/RegistryPage'
import CrmModuleDetailPage from '../features/crmModules/CrmModuleDetailPage'
import CrmModulesPage from '../features/crmModules/CrmModulesPage'
import AiArchitectPage from '../features/aiArchitect/AiArchitectPage'
import AnimatorSchedulePage from '../features/animatorSchedule/AnimatorSchedulePage'
import EmployeeEvaluationsPage from '../features/employeeEvaluations/EmployeeEvaluationsPage'
import MarketHome from '../pages/MarketHome'
import MarketSectionPage from '../pages/MarketSectionPage'
import { configureCrmPlatformApiBase } from '../shared/apiBase'
import { useAppLayoutContext } from '../shared/appLayoutContext'
import { useI18n } from '../shared/i18nContext'
import { isModuleEnabled, type ModuleId } from '../shared/modules'

configureCrmPlatformApiBase()

const resolveBasename = () => {
  if (typeof window === 'undefined') return undefined
  return window.location.pathname.startsWith('/crm_platform') ? '/crm_platform' : undefined
}

const ModuleRoute = ({ moduleId, children }: { moduleId: ModuleId; children: ReactElement }) => {
  const { enabledModules, modulesLoaded } = useAppLayoutContext()
  const { t } = useI18n()

  if (!modulesLoaded) return <div className="crm-loading-state">{t('common.loading')}</div>
  if (!isModuleEnabled(enabledModules, moduleId)) {
    return (
      <div className="crm-page-shell">
        <section className="section crm-section-panel">
          <div className="section-head">
            <h1 className="section-title">{t('modules.disabled')}</h1>
          </div>
        </section>
      </div>
    )
  }
  return children
}

function App() {
  const basename = resolveBasename()

  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route element={<AppLayout />}>
          <Route path="/home" element={<ModuleRoute moduleId="workspace_home"><MarketHome /></ModuleRoute>} />
          <Route path="/people" element={<ModuleRoute moduleId="workspace_home"><MarketSectionPage sectionId="people" /></ModuleRoute>} />
          <Route path="/work" element={<ModuleRoute moduleId="workspace_home"><MarketSectionPage sectionId="work" /></ModuleRoute>} />
          <Route path="/money" element={<ModuleRoute moduleId="workspace_home"><MarketSectionPage sectionId="money" /></ModuleRoute>} />
          <Route path="/settings" element={<ModuleRoute moduleId="workspace_home"><MarketSectionPage sectionId="settings" /></ModuleRoute>} />
          <Route path="/ai-architect" element={<ModuleRoute moduleId="ai_architect"><AiArchitectPage /></ModuleRoute>} />
          <Route path="/animator-schedule" element={<ModuleRoute moduleId="animator_schedule"><AnimatorSchedulePage /></ModuleRoute>} />
          <Route path="/employee-evaluations" element={<ModuleRoute moduleId="employee_evaluations"><EmployeeEvaluationsPage /></ModuleRoute>} />
          <Route path="/dashboard" element={<ModuleRoute moduleId="dashboard"><Dashboard /></ModuleRoute>} />
          <Route path="/profile" element={<ModuleRoute moduleId="profile"><Profile /></ModuleRoute>} />
          <Route path="/requests" element={<ModuleRoute moduleId="open_requests"><RequestsPage /></ModuleRoute>} />
          <Route path="/requests/assigned" element={<ModuleRoute moduleId="assigned_work"><AssignedRequestsPage /></ModuleRoute>} />
          <Route path="/requests/my" element={<Navigate to="/requests/assigned" replace />} />
          <Route path="/requests/history" element={<ModuleRoute moduleId="request_history"><RequestsHistoryPage /></ModuleRoute>} />
          <Route path="/requests/:id" element={<ModuleRoute moduleId="open_requests"><RequestDetailsPage /></ModuleRoute>} />
          <Route path="/departments" element={<ModuleRoute moduleId="departments"><DepartmentsPage /></ModuleRoute>} />
          <Route path="/registry" element={<ModuleRoute moduleId="registry"><RegistryPage /></ModuleRoute>} />
          <Route path="/forms" element={<ModuleRoute moduleId="form_templates"><TemplatesPage /></ModuleRoute>} />
          <Route path="/forms/new" element={<ModuleRoute moduleId="form_builder"><TemplateBuilderPage /></ModuleRoute>} />
          <Route path="/forms/:id/edit" element={<ModuleRoute moduleId="form_builder"><TemplateBuilderPage /></ModuleRoute>} />
          <Route path="/forms/:id/fill" element={<ModuleRoute moduleId="form_templates"><FormFillPage /></ModuleRoute>} />
          <Route path="/forms/:id/records" element={<ModuleRoute moduleId="form_templates"><FormRecordsPage /></ModuleRoute>} />
          <Route path="/forms/:id/queue" element={<ModuleRoute moduleId="form_templates"><FormQueuePage /></ModuleRoute>} />
          <Route path="/files" element={<ModuleRoute moduleId="files"><FilesPage /></ModuleRoute>} />
          <Route path="/reports" element={<ModuleRoute moduleId="report_library"><ReportsPage /></ModuleRoute>} />
          <Route path="/report-types" element={<ModuleRoute moduleId="report_types"><ReportTypesPage /></ModuleRoute>} />
          <Route path="/modules" element={<CrmModulesPage />} />
          <Route path="/modules/:moduleId" element={<CrmModuleDetailPage />} />
          <Route path="/admin" element={<ModuleRoute moduleId="admin_panel"><AdminPage /></ModuleRoute>} />
          <Route path="/superadmin" element={<ModuleRoute moduleId="superadmin_panel"><WorkspaceManagementPage /></ModuleRoute>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
