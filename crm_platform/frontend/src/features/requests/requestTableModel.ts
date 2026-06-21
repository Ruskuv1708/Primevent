import type { FormField, FormTemplate } from '../forms/types'
import { getEffectiveRequestPriority } from './priority'
import type { RequestItem } from './types'

export type RequestTableSortDirection = 'asc' | 'desc'

export type RequestTableSortState = {
  columnId: string | null
  direction: RequestTableSortDirection | null
}

export type RequestTableColumn = {
  id: string
  label: string
  sortable: boolean
  defaultDirection?: RequestTableSortDirection
}

type DynamicColumn = RequestTableColumn & {
  aliases: string[]
}

export type RequestTableRow = {
  request: RequestItem
  dateText: string
  openForText: string
  templateName: string
  statusText: string
  priority: string
  departmentName: string
  assignedName: string
  dynamicValues: Record<string, string>
  sortValues: Record<string, string | number>
}

export type RequestTableModel = {
  columns: RequestTableColumn[]
  rows: RequestTableRow[]
}

type BuildRequestTableModelArgs = {
  requests: RequestItem[]
  templates: FormTemplate[]
  resolveDepartmentName: (departmentId?: string | null) => string
  resolveAssignedName: (request: RequestItem) => string
}

const PRIORITY_RANK: Record<string, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
}

const STATUS_RANK: Record<string, number> = {
  new: 1,
  assigned: 2,
  in_process: 3,
  pending: 4,
  done: 5,
}

const normalizeId = (value?: string | null): string | null => {
  if (!value) return null
  return String(value).toLowerCase()
}

const normalizeKey = (value?: string | null): string => {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '')
}

const isSystemAttribute = (value?: string | null): boolean => {
  const key = normalizeKey(value)
  return (
    key === 'status'
    || key === 'priority'
    || key === 'department'
    || key === 'departmentid'
    || key === 'assignedto'
    || key === 'assignedtoid'
    || key === 'created'
    || key === 'createdat'
    || key === 'date'
    || key === 'template'
    || key === 'title'
    || key === 'request'
    || key === 'requestid'
  )
}

const parseAttributesFromDescription = (description?: string | null): Map<string, string> => {
  const attributes = new Map<string, string>()
  if (!description) return attributes

  const normalized = String(description)
    .replace(/\r/g, '\n')
    .replace(/\n+/g, ' • ')
    .replace(/\s{2,}/g, ' ')
    .trim()

  if (!normalized) return attributes

  const chunks = normalized
    .split(/(?:•|\|)/g)
    .map(part => part.trim())
    .filter(Boolean)

  for (const chunk of chunks) {
    const colonIndex = chunk.indexOf(':')
    if (colonIndex <= 0) continue
    const rawKey = chunk.slice(0, colonIndex).trim()
    const rawValue = chunk.slice(colonIndex + 1).trim()
    if (!rawKey || !rawValue) continue
    attributes.set(normalizeKey(rawKey), rawValue)
  }

  if (attributes.size > 0) return attributes

  const fallbackMatches = Array.from(
    normalized.matchAll(/([A-Za-z0-9/_ -]+):\s*([^:]+?)(?=\s+[A-Za-z0-9/_ -]+:|$)/g),
  )
  for (const match of fallbackMatches) {
    const rawKey = match[1]?.trim()
    const rawValue = match[2]?.trim()
    if (!rawKey || !rawValue) continue
    attributes.set(normalizeKey(rawKey), rawValue)
  }

  return attributes
}

const isBuiltinField = (field: FormField): boolean => {
  const fieldType = String(field.type || '').toLowerCase()
  if (fieldType === 'status_select' || fieldType === 'priority_select' || fieldType === 'department_select') {
    return true
  }
  return isSystemAttribute(field.key) || isSystemAttribute(field.label)
}

const mergeAliases = (column: DynamicColumn, nextAliases: string[]) => {
  const known = new Set(column.aliases)
  nextAliases.forEach(alias => {
    if (!alias || known.has(alias)) return
    known.add(alias)
    column.aliases.push(alias)
  })
}

const collectDynamicColumns = (
  requests: RequestItem[],
  templateMap: Map<string, FormTemplate>,
  parsedByRequestId: Map<string, Map<string, string>>,
): DynamicColumn[] => {
  const dynamic = new Map<string, DynamicColumn>()

  const findMatchingColumnId = (label: string, aliases: string[]) => {
    const normalizedLabel = normalizeKey(label)
    for (const [existingId, existing] of dynamic.entries()) {
      if (aliases.some(alias => alias && existing.aliases.includes(alias))) {
        return existingId
      }
      if (normalizedLabel && normalizeKey(existing.label) === normalizedLabel) {
        return existingId
      }
    }
    return null
  }

  const ensureColumn = (
    columnId: string,
    label: string,
    aliases: string[],
    source: 'template' | 'parsed',
  ) => {
    if (!columnId || isSystemAttribute(columnId) || isSystemAttribute(label)) return
    const nextAliases = Array.from(new Set(aliases.filter(Boolean)))
    const matchedColumnId = dynamic.has(columnId) ? columnId : findMatchingColumnId(label, nextAliases)
    if (matchedColumnId) {
      const existing = dynamic.get(matchedColumnId)!
      mergeAliases(existing, nextAliases)
      const existingLooksGenerated = existing.label === normalizeKey(existing.label)
      if (source === 'template' && existingLooksGenerated && label && normalizeKey(label) !== normalizeKey(existing.label)) {
        existing.label = label
      }
      return
    }

    if (!dynamic.has(columnId)) {
      dynamic.set(columnId, {
        id: columnId,
        label,
        sortable: true,
        aliases: nextAliases,
      })
      return
    }
    mergeAliases(dynamic.get(columnId)!, nextAliases)
  }

  requests.forEach(request => {
    const templateId = normalizeId(request?.meta_data?.template_id as string | undefined)
    const template = templateId ? templateMap.get(templateId) || null : null

    ;(template?.schema_structure || []).forEach(field => {
      if (isBuiltinField(field)) return
      const keyAlias = normalizeKey(field.key)
      const labelAlias = normalizeKey(field.label || field.key)
      const aliases = [keyAlias, labelAlias].filter(Boolean)
      const baseAlias = keyAlias || labelAlias
      if (!baseAlias) return
      ensureColumn(`attr:${baseAlias}`, field.label || field.key || 'Attribute', aliases, 'template')
    })

    const parsed = parsedByRequestId.get(request.id) || new Map<string, string>()
    parsed.forEach((_value, parsedKey) => {
      if (!parsedKey || isSystemAttribute(parsedKey)) return
      ensureColumn(`attr:${parsedKey}`, parsedKey.replace(/_/g, ' '), [parsedKey], 'parsed')
    })
  })

  return Array.from(dynamic.values())
}

const columnLabelSort = (a: DynamicColumn, b: DynamicColumn) => {
  return a.label.localeCompare(b.label, undefined, { sensitivity: 'base' })
}

const getTemplateName = (request: RequestItem, templateMap: Map<string, FormTemplate>): string => {
  const templateId = normalizeId(request?.meta_data?.template_id as string | undefined)
  if (templateId) {
    const template = templateMap.get(templateId)
    if (template?.name) return template.name
  }
  return request?.title || 'Unknown template'
}

const resolveDynamicValue = (aliases: string[], parsedMap: Map<string, string>): string => {
  for (const alias of aliases) {
    if (!alias) continue
    const value = parsedMap.get(alias)
    if (typeof value === 'string' && value.trim().length > 0) {
      return value.trim()
    }
  }
  return '—'
}

const formatDurationMs = (durationMs: number): string => {
  if (!Number.isFinite(durationMs) || durationMs <= 0) return '0m'
  const totalMinutes = Math.floor(durationMs / 60000)
  const days = Math.floor(totalMinutes / (60 * 24))
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60)
  const minutes = totalMinutes % 60

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export const buildRequestTableModel = ({
  requests,
  templates,
  resolveDepartmentName,
  resolveAssignedName,
}: BuildRequestTableModelArgs): RequestTableModel => {
  const templateMap = new Map<string, FormTemplate>()
  templates.forEach(template => {
    const key = normalizeId(template.id)
    if (!key) return
    templateMap.set(key, template)
  })

  const parsedByRequestId = new Map<string, Map<string, string>>()
  requests.forEach(request => {
    parsedByRequestId.set(request.id, parseAttributesFromDescription(request.description))
  })

  const dynamicColumns = collectDynamicColumns(requests, templateMap, parsedByRequestId).sort(columnLabelSort)

  const columns: RequestTableColumn[] = [
    { id: 'date', label: 'Date', sortable: true, defaultDirection: 'desc' },
    { id: 'uptime', label: 'Open For', sortable: true, defaultDirection: 'desc' },
    { id: 'template', label: 'Template', sortable: true },
    ...dynamicColumns.map(column => ({
      id: column.id,
      label: column.label,
      sortable: column.sortable,
      defaultDirection: column.defaultDirection,
    })),
    { id: 'status', label: 'Status', sortable: true },
    { id: 'priority', label: 'Priority', sortable: true },
    { id: 'department', label: 'Department', sortable: true },
    { id: 'assigned_to', label: 'Assigned To', sortable: true },
  ]

  const rows: RequestTableRow[] = requests.map(request => {
    const parsedMap = parsedByRequestId.get(request.id) || new Map<string, string>()
    const templateName = getTemplateName(request, templateMap)
    const createdAtMs = new Date(request.created_at || 0).getTime()
    const nowMs = Date.now()
    const openForMs = Number.isNaN(createdAtMs) ? 0 : Math.max(0, nowMs - createdAtMs)
    const priority = getEffectiveRequestPriority(request)
    const departmentName = resolveDepartmentName(request.department_id)
    const assignedName = resolveAssignedName(request)

    const dynamicValues: Record<string, string> = {}
    dynamicColumns.forEach(column => {
      dynamicValues[column.id] = resolveDynamicValue(column.aliases, parsedMap)
    })

    const sortValues: Record<string, string | number> = {
      date: Number.isNaN(createdAtMs) ? 0 : createdAtMs,
      uptime: openForMs,
      template: templateName.toLowerCase(),
      status: STATUS_RANK[request.status || 'new'] || 0,
      priority: PRIORITY_RANK[priority] || 0,
      department: departmentName.toLowerCase(),
      assigned_to: assignedName.toLowerCase(),
    }

    dynamicColumns.forEach(column => {
      sortValues[column.id] = (dynamicValues[column.id] || '').toLowerCase()
    })

    return {
      request,
      dateText: request.created_at ? new Date(request.created_at).toLocaleDateString() : '—',
      openForText: formatDurationMs(openForMs),
      templateName,
      statusText: String(request.status || '').replace(/_/g, ' ').toUpperCase(),
      priority,
      departmentName,
      assignedName,
      dynamicValues,
      sortValues,
    }
  })

  return { columns, rows }
}

const compareValues = (
  a: string | number | undefined,
  b: string | number | undefined,
  direction: RequestTableSortDirection,
) => {
  const left = a ?? ''
  const right = b ?? ''
  let result = 0
  if (typeof left === 'number' || typeof right === 'number') {
    result = Number(left || 0) - Number(right || 0)
  } else {
    result = String(left).localeCompare(String(right), undefined, { sensitivity: 'base' })
  }
  return direction === 'asc' ? result : -result
}

export const sortRequestTableRows = (
  rows: RequestTableRow[],
  sortState: RequestTableSortState,
): RequestTableRow[] => {
  if (!sortState.columnId || !sortState.direction) {
    return [...rows]
  }

  const { columnId, direction } = sortState

  return [...rows].sort((a, b) => {
    const byColumn = compareValues(a.sortValues[columnId], b.sortValues[columnId], direction)
    if (byColumn !== 0) return byColumn
    return compareValues(a.sortValues.date, b.sortValues.date, 'desc')
  })
}

export const getNextSortState = (
  columns: RequestTableColumn[],
  currentState: RequestTableSortState,
  nextColumnId: string,
): RequestTableSortState => {
  const nextColumn = columns.find(column => column.id === nextColumnId)
  if (!nextColumn) return currentState

  if (currentState.columnId !== nextColumnId || !currentState.direction) {
    return {
      columnId: nextColumnId,
      direction: nextColumn.defaultDirection || 'asc',
    }
  }

  if (currentState.direction === 'asc') {
    return {
      columnId: nextColumnId,
      direction: 'desc',
    }
  }

  if (currentState.direction === 'desc') {
    return {
      columnId: null,
      direction: null,
    }
  }

  return {
    columnId: nextColumnId,
    direction: nextColumn.defaultDirection || 'asc',
  }
}
