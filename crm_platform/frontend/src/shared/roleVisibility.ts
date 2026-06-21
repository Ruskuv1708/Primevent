import type { FormField } from '../features/forms/types'
import { roleMatches } from './roleLabels'

export type RoleVisibilityPermissions = {
  tabs?: Record<string, boolean>
  fields?: Record<string, Record<string, boolean>>
}

type UserWithCustomRole = {
  role?: string
  custom_role?: {
    permissions?: RoleVisibilityPermissions | null
  } | null
} | null | undefined

const DEFAULT_TAB_ROLES: Record<string, string[]> = {
  ai_architect: ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'],
  admin: ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'],
  superadmin: ['SUPERADMIN'],
}

const permissionsFor = (user: UserWithCustomRole): RoleVisibilityPermissions | null => {
  return user?.custom_role?.permissions || null
}

export const canViewTab = (user: UserWithCustomRole, tabKey: string) => {
  const tabs = permissionsFor(user)?.tabs
  const defaultRoles = DEFAULT_TAB_ROLES[tabKey]
  if (defaultRoles && !roleMatches(user?.role, defaultRoles)) return false
  if (!tabs || !(tabKey in tabs)) return true
  return tabs[tabKey] !== false
}

export const formFieldVisibilityKey = (templateId: string | null | undefined, fieldKey: string) => {
  return templateId ? `${templateId}:${fieldKey}` : fieldKey
}

export const canViewFormField = (
  user: UserWithCustomRole,
  templateId: string | null | undefined,
  fieldKey: string,
) => {
  const formFields = permissionsFor(user)?.fields?.forms
  if (!formFields) return true

  const scopedKey = formFieldVisibilityKey(templateId, fieldKey)
  if (scopedKey in formFields) return formFields[scopedKey] !== false
  if (fieldKey in formFields) return formFields[fieldKey] !== false
  return true
}

export const filterVisibleFormFields = (
  user: UserWithCustomRole,
  templateId: string | null | undefined,
  fields: FormField[],
) => fields.filter(field => canViewFormField(user, templateId, field.key))
