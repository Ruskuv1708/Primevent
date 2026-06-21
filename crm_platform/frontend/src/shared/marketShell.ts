import type { ModuleId } from './modules'

export type MarketSectionId = 'home' | 'people' | 'work' | 'money' | 'reports' | 'settings'

export type MarketQuickAction = {
  id: string
  label: string
  to: string
}

export type MarketWidget = {
  id: string
  label: string
  tone: 'neutral' | 'attention' | 'success'
  source: 'requests' | 'templates' | 'schedule' | 'static'
}

export type MarketShell = {
  modulePreset: string
  label: string
  primaryPeopleLabel: string
  sections: Record<MarketSectionId, string>
  quickActions: MarketQuickAction[]
  widgets: MarketWidget[]
  enabledModules: ModuleId[]
}

const COMMON_SECTIONS = {
  home: 'Home',
  people: 'Clients',
  work: 'Work',
  money: 'Money',
  reports: 'Reports',
  settings: 'Settings',
} as const

const CORE_MODULES: ModuleId[] = [
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

const GENERAL_SHELL: MarketShell = {
  modulePreset: 'functional',
  label: 'Functional CRM',
  primaryPeopleLabel: 'Customers',
  sections: COMMON_SECTIONS,
  quickActions: [
    { id: 'new-request', label: 'Create request', to: '/requests' },
    { id: 'new-client', label: 'Add customer', to: '/registry' },
    { id: 'open-schedule', label: 'Open schedule', to: '/animator-schedule' },
    { id: 'ai-architect', label: 'Open AI Architect', to: '/ai-architect' },
  ],
  widgets: [
    { id: 'attention', label: 'Needs attention', tone: 'attention', source: 'requests' },
    { id: 'recent-work', label: 'Recent work', tone: 'neutral', source: 'requests' },
    { id: 'schedule-conflicts', label: 'Schedule conflicts', tone: 'attention', source: 'schedule' },
  ],
  enabledModules: CORE_MODULES,
}

export const getMarketShell = (): MarketShell => GENERAL_SHELL
