export type RequestPriorityValue = 'low' | 'medium' | 'high' | 'critical'

const PRIORITY_ORDER: RequestPriorityValue[] = ['low', 'medium', 'high', 'critical']

const isObject = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === 'object'

export const normalizePriority = (value?: string | null): RequestPriorityValue | null => {
  if (!value) return null
  const normalized = String(value).trim().toLowerCase()
  return PRIORITY_ORDER.includes(normalized as RequestPriorityValue)
    ? (normalized as RequestPriorityValue)
    : null
}

const readPriorityFromDescription = (description?: string | null): RequestPriorityValue | null => {
  if (!description) return null
  const match = description.match(/\bpriority\s*:\s*(critical|high|medium|low)\b/i)
  return normalizePriority(match?.[1] || null)
}

const readPriorityFromMeta = (metaData?: Record<string, unknown> | null): RequestPriorityValue | null => {
  if (!metaData || !isObject(metaData)) return null

  const direct = normalizePriority(String(metaData.priority || ''))
  if (direct) return direct

  const requestPriority = normalizePriority(String(metaData.request_priority || ''))
  if (requestPriority) return requestPriority

  return null
}

export const getEffectiveRequestPriority = (request: {
  priority?: string | null
  description?: string | null
  meta_data?: Record<string, unknown> | null
}): RequestPriorityValue => {
  const directPriority = normalizePriority(request.priority || null)
  const metaPriority = readPriorityFromMeta(request.meta_data || null)
  const descriptionPriority = readPriorityFromDescription(request.description || null)

  if (directPriority && directPriority !== 'medium') {
    return directPriority
  }

  return metaPriority || descriptionPriority || directPriority || 'medium'
}

export const getPriorityColor = (priority: string) => {
  const normalized = normalizePriority(priority) || 'low'
  switch (normalized) {
    case 'critical':
      return '#ff4d4f'
    case 'high':
      return '#faad14'
    case 'medium':
      return '#1890ff'
    default:
      return '#52c41a'
  }
}
