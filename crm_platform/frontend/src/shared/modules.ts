export type ModuleId =
  | 'workspace_home'
  | 'dashboard'
  | 'registry'
  | 'workflow'
  | 'open_requests'
  | 'assigned_work'
  | 'request_history'
  | 'departments'
  | 'animator_schedule'
  | 'employee_evaluations'
  | 'dynamic_forms'
  | 'form_templates'
  | 'form_builder'
  | 'files'
  | 'reports'
  | 'report_library'
  | 'report_types'
  | 'notifications'
  | 'profile'
  | 'ai_architect'
  | 'admin_panel'
  | 'superadmin_panel'

export type ModuleDefinition = {
  id: ModuleId
  label: string
  category: 'functional'
  description: string
  route_path: string
  summary: string
  capabilities: string[]
  dependencies: ModuleId[]
  synergies: {
    module_id: ModuleId
    label: string
    description: string
  }[]
  default_enabled: boolean
}

export type ModuleTemplate = {
  id: string
  label: string
  template_type: 'registry' | 'workflow' | 'form' | 'report' | string
  description: string
  fields: string[]
  stages: string[]
}

export type ModuleManifest = {
  module_id: ModuleId
  label: string
  summary: string
  templates: ModuleTemplate[]
}

export type ModuleInstallStatus = {
  module_id: ModuleId
  label: string
  total_templates: number
  installed_count: number
  is_installed: boolean
  installed_template_ids: string[]
  missing_template_ids: string[]
}

export type ModuleInstallResult = ModuleInstallStatus & {
  created_form_template_count: number
  created_report_type_count: number
}

export type WorkspaceModuleSettings = {
  module_preset?: string
  enabled_modules: string[]
}

export const DEFAULT_ENABLED_MODULES: ModuleId[] = [
  'workspace_home',
  'dashboard',
  'registry',
  'workflow',
  'open_requests',
  'assigned_work',
  'request_history',
  'departments',
  'animator_schedule',
  'employee_evaluations',
  'dynamic_forms',
  'form_templates',
  'form_builder',
  'files',
  'reports',
  'report_library',
  'report_types',
  'notifications',
  'profile',
  'ai_architect',
  'admin_panel',
  'superadmin_panel',
]

export const isModuleEnabled = (enabledModules: string[], moduleId: ModuleId) => {
  return enabledModules.includes(moduleId)
}

export const getWorkspaceModuleSettings = (workspace: any): WorkspaceModuleSettings => {
  const settings = workspace?.settings && typeof workspace.settings === 'object' ? workspace.settings : {}
  const enabled = Array.isArray(settings.enabled_modules)
    ? settings.enabled_modules.filter((item: unknown): item is string => typeof item === 'string')
    : DEFAULT_ENABLED_MODULES
  return {
    module_preset: typeof settings.module_preset === 'string' ? settings.module_preset : 'functional',
    enabled_modules: enabled,
  }
}

export const getModuleCategoryLabel = (category: string) => {
  if (category === 'functional') return 'Functional Modules'
  return 'Modules'
}

export const getTemplateTypeLabel = (templateType: string) => {
  if (templateType === 'registry') return 'Registry'
  if (templateType === 'workflow') return 'Workflow'
  if (templateType === 'form') return 'Dynamic Form'
  if (templateType === 'report') return 'Report'
  return templateType
}
