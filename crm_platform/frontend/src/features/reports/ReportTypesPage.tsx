import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

import theme from '../../shared/theme'
import { normalizeRole, roleMatches } from '../../shared/roleLabels'
import { getWorkspaceParams } from '../../shared/workspace'
import useIsMobile from '../../shared/useIsMobile'

type ReportTypeColumn = {
  key: string
  label: string
  formula?: string | null
  format?: string | null
}

type ReportTypeItem = {
  id: string
  name: string
  description?: string | null
  source: 'requests' | 'users' | 'clients' | 'companies' | 'custom'
  columns: ReportTypeColumn[]
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

type ReportSource = ReportTypeItem['source']
type ObjectSource = Exclude<ReportSource, 'custom'>
type ImportSourceSelection = ReportSource | 'auto'

type RequestObject = {
  id?: string
  title?: string | null
  description?: string | null
  status?: string | null
  priority?: string | null
  created_at?: string | null
  updated_at?: string | null
  department_id?: string | null
  assigned_to_id?: string | null
  assignee?: {
    id?: string
    full_name?: string | null
  } | null
}

type UserObject = {
  id?: string
  full_name?: string | null
  email?: string | null
  role?: string | null
  is_active?: boolean
  department_id?: string | null
}

type ClientObject = {
  id?: string
  first_name?: string | null
  last_name?: string | null
  email?: string | null
  phone?: string | null
  company_name?: string | null
  status?: string | null
  status_label?: string | null
}

type CompanyObject = {
  id?: string
  name?: string | null
  registration_number?: string | null
  email?: string | null
  phone?: string | null
  address?: string | null
}

type ColumnBinding = {
  source: ObjectSource
  key: string
  label: string
}

type CellBorders = {
  top: boolean
  right: boolean
  bottom: boolean
  left: boolean
}

type CellStyle = {
  fillColor: string | null
  textColor: string | null
  bold: boolean
  italic: boolean
  align: 'left' | 'center' | 'right'
  borders: CellBorders
}

type SpreadsheetCell = {
  value: string
  binding: ColumnBinding | null
  style: CellStyle
}

type CellPosition = {
  row: number
  col: number
}

type FillDragState = {
  source: CellPosition
  end: CellPosition
}

type FillRange = {
  minRow: number
  maxRow: number
  minCol: number
  maxCol: number
}

type PaletteField = ColumnBinding & {
  id: string
  description: string
  preview: string
  sample: string
}

type GuideModal = {
  title: string
  message: string
  steps: string[]
}

const SOURCE_OPTIONS: Array<{ value: ReportSource; label: string }> = [
  { value: 'requests', label: 'Requests' },
  { value: 'users', label: 'Users' },
  { value: 'clients', label: 'Clients' },
  { value: 'companies', label: 'Companies' },
  { value: 'custom', label: 'Custom dataset' },
]

const IMPORT_SOURCE_OPTIONS: Array<{ value: ImportSourceSelection; label: string }> = [
  { value: 'auto', label: 'Auto detect' },
  ...SOURCE_OPTIONS,
]

const GRID_ROWS = 20
const GRID_COLS = 14
const DRAG_FIELD_MIME = 'application/x-crm-report-field'
const DEFAULT_CELL_BORDER_COLOR = '#d9d9d9'
const CUSTOM_CELL_BORDER_COLOR = '#4b5563'

const DEFAULT_CELL_STYLE: CellStyle = {
  fillColor: null,
  textColor: null,
  bold: false,
  italic: false,
  align: 'left',
  borders: {
    top: false,
    right: false,
    bottom: false,
    left: false,
  },
}

const SOURCE_COLORS: Record<ObjectSource, { accent: string; background: string; text: string }> = {
  requests: {
    accent: '#1d4ed8',
    background: '#dbeafe',
    text: '#1e3a8a',
  },
  users: {
    accent: '#0f766e',
    background: '#ccfbf1',
    text: '#115e59',
  },
  clients: {
    accent: '#7c3aed',
    background: '#ede9fe',
    text: '#5b21b6',
  },
  companies: {
    accent: '#b45309',
    background: '#fef3c7',
    text: '#92400e',
  },
}

const normalizeUser = (user: any) => ({
  ...user,
  role: normalizeRole(user.role),
})

const cloneCellStyle = (style: CellStyle): CellStyle => ({
  fillColor: style.fillColor,
  textColor: style.textColor,
  bold: style.bold,
  italic: style.italic,
  align: style.align,
  borders: { ...style.borders },
})

const buildEmptyCell = (): SpreadsheetCell => ({
  value: '',
  binding: null,
  style: cloneCellStyle(DEFAULT_CELL_STYLE),
})

const buildEmptyGrid = () =>
  Array.from({ length: GRID_ROWS }, () =>
    Array.from({ length: GRID_COLS }, () => buildEmptyCell()),
  )

const cloneGrid = (grid: SpreadsheetCell[][]) =>
  grid.map(row => row.map(cell => ({
    ...cell,
    binding: cell.binding ? { ...cell.binding } : null,
    style: cloneCellStyle(cell.style || DEFAULT_CELL_STYLE),
  })))

const normalizeCellPosition = (position: CellPosition): CellPosition => ({
  row: Math.min(Math.max(position.row, 0), GRID_ROWS - 1),
  col: Math.min(Math.max(position.col, 0), GRID_COLS - 1),
})

const getFillRange = (start: CellPosition, end: CellPosition): FillRange => {
  const from = normalizeCellPosition(start)
  const to = normalizeCellPosition(end)
  return {
    minRow: Math.min(from.row, to.row),
    maxRow: Math.max(from.row, to.row),
    minCol: Math.min(from.col, to.col),
    maxCol: Math.max(from.col, to.col),
  }
}

const getColumnLabel = (index: number) => {
  let value = index + 1
  let output = ''
  while (value > 0) {
    const remainder = (value - 1) % 26
    output = String.fromCharCode(65 + remainder) + output
    value = Math.floor((value - 1) / 26)
  }
  return output
}

const toSafeKey = (value: string, fallback: string) => {
  const sanitized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

  if (!sanitized) return fallback
  return sanitized.slice(0, 120)
}

const valueToText = (value: unknown): string => {
  if (value === null || typeof value === 'undefined') return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}

const findFirstValue = <T,>(items: T[], resolver: (item: T) => unknown) => {
  for (const item of items) {
    const resolved = valueToText(resolver(item))
    if (resolved) return resolved
  }
  return ''
}

const formatDateText = (value?: string | null) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString()
}

const formatPreview = (value: string) => {
  if (!value) return '(no sample data)'
  if (value.length <= 72) return value
  return `${value.slice(0, 69)}...`
}

const isObjectSource = (source: string): source is ObjectSource => {
  return source === 'requests' || source === 'users' || source === 'clients' || source === 'companies'
}

const toGoogleSheetEmbeddedEditorUrl = (rawUrl: string) => {
  const idMatch = rawUrl.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/)
  const sheetId = idMatch?.[1]
  if (!sheetId) return null

  let gid = ''
  try {
    const parsed = new URL(rawUrl)
    gid = parsed.searchParams.get('gid') || ''
    if (!gid && parsed.hash.includes('gid=')) {
      const hashMatch = parsed.hash.match(/gid=([0-9]+)/)
      gid = hashMatch?.[1] || ''
    }
  } catch {
    const fallbackMatch = rawUrl.match(/gid=([0-9]+)/)
    gid = fallbackMatch?.[1] || ''
  }

  return gid
    ? `https://docs.google.com/spreadsheets/d/${sheetId}/edit#gid=${gid}`
    : `https://docs.google.com/spreadsheets/d/${sheetId}/edit`
}

function ReportTypesPage() {
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const [currentUser, setCurrentUser] = useState<any>(null)
  const [reportTypes, setReportTypes] = useState<ReportTypeItem[]>([])
  const [requestsData, setRequestsData] = useState<RequestObject[]>([])
  const [usersData, setUsersData] = useState<UserObject[]>([])
  const [clientsData, setClientsData] = useState<ClientObject[]>([])
  const [companiesData, setCompaniesData] = useState<CompanyObject[]>([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [importingFile, setImportingFile] = useState(false)
  const [importingGoogle, setImportingGoogle] = useState(false)
  const [fileInputResetKey, setFileInputResetKey] = useState(0)
  const [objectsLoading, setObjectsLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [guideModal, setGuideModal] = useState<GuideModal | null>(null)
  const [objectsWarning, setObjectsWarning] = useState<string | null>(null)
  const [paletteSearch, setPaletteSearch] = useState('')

  const [selectedCell, setSelectedCell] = useState<CellPosition>({ row: 0, col: 0 })
  const [grid, setGrid] = useState<SpreadsheetCell[][]>(() => buildEmptyGrid())
  const [isSpreadsheetFullscreen, setIsSpreadsheetFullscreen] = useState(false)
  const [fillDragState, setFillDragState] = useState<FillDragState | null>(null)
  const [embeddedGoogleEditorUrl, setEmbeddedGoogleEditorUrl] = useState<string | null>(null)

  const [form, setForm] = useState({
    name: '',
    description: '',
    source: 'requests' as ReportSource,
    is_active: true,
  })

  const [fileImportForm, setFileImportForm] = useState({
    file: null as File | null,
    name: '',
    description: '',
    source: 'auto' as ImportSourceSelection,
    is_active: true,
    header_row: 1,
    worksheet_name: '',
  })

  const [googleImportForm, setGoogleImportForm] = useState({
    name: '',
    google_sheet_url: '',
    description: '',
    source: 'auto' as ImportSourceSelection,
    is_active: true,
    header_row: 1,
    worksheet_gid: '',
  })

  const canManageReportTypes = useMemo(() => {
    if (!currentUser) return false
    return roleMatches(currentUser.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])
  }, [currentUser])

  const readToken = () => localStorage.getItem('crm_token')

  const handleUnauthorized = () => {
    localStorage.removeItem('crm_token')
    navigate('/')
  }

  const fetchCurrentUser = async () => {
    const token = readToken()
    if (!token) {
      handleUnauthorized()
      return null
    }
    const res = await axios.get('/access/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const normalized = normalizeUser(res.data)
    setCurrentUser(normalized)
    return normalized
  }

  const fetchReportTypes = async (user: any) => {
    const token = readToken()
    if (!token) return
    const res = await axios.get('/reports/types', {
      headers: { Authorization: `Bearer ${token}` },
      params: {
        ...(getWorkspaceParams(user) || {}),
        include_inactive: true,
      },
    })
    setReportTypes(Array.isArray(res.data) ? res.data : [])
  }

  const fetchObjectSamples = async (user: any) => {
    const token = readToken()
    if (!token) return
    setObjectsLoading(true)
    setObjectsWarning(null)

    const params = getWorkspaceParams(user) || {}
    const headers = { Authorization: `Bearer ${token}` }

    const [requestsRes, usersRes, clientsRes, companiesRes] = await Promise.allSettled([
      axios.get('/workflow/requests', { headers, params }),
      axios.get('/access/users', { headers, params: { ...params, limit: 50 } }),
      axios.get('/registry/clients', { headers, params }),
      axios.get('/registry/companies', { headers, params }),
    ])

    const failedSources: string[] = []
    let unauthorizedDetected = false

    const readResult = <T,>(result: PromiseSettledResult<any>, fallbackLabel: string): T[] => {
      if (result.status === 'fulfilled') {
        return Array.isArray(result.value?.data) ? (result.value.data as T[]) : []
      }
      if (result.reason?.response?.status === 401) {
        unauthorizedDetected = true
        return []
      }
      failedSources.push(fallbackLabel)
      return []
    }

    setRequestsData(readResult<RequestObject>(requestsRes, 'requests'))
    setUsersData(readResult<UserObject>(usersRes, 'users'))
    setClientsData(readResult<ClientObject>(clientsRes, 'clients'))
    setCompaniesData(readResult<CompanyObject>(companiesRes, 'companies'))

    if (unauthorizedDetected) {
      setObjectsLoading(false)
      handleUnauthorized()
      return
    }

    if (failedSources.length > 0) {
      setObjectsWarning(`Some object catalogs could not be loaded: ${failedSources.join(', ')}.`)
    }

    setObjectsLoading(false)
  }

  useEffect(() => {
    ;(async () => {
      try {
        const user = await fetchCurrentUser()
        if (!user) return
        if (!roleMatches(user.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])) {
          setError('Report types page is available for superadmin/system admin/admin roles.')
          return
        }
        await Promise.all([fetchReportTypes(user), fetchObjectSamples(user)])
      } catch (err: any) {
        if (err?.response?.status === 401) {
          handleUnauthorized()
          return
        }
        setError(err?.response?.data?.detail || 'Failed to load report types')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const paletteGroups = useMemo(() => {
    const requestFields: PaletteField[] = [
      {
        id: 'requests.title',
        source: 'requests',
        key: 'title',
        label: 'Request Title',
        description: 'Request title from workflow queue',
        sample: findFirstValue(requestsData, item => item.title),
        preview: '',
      },
      {
        id: 'requests.status',
        source: 'requests',
        key: 'status',
        label: 'Request Status',
        description: 'Current request status',
        sample: findFirstValue(requestsData, item => item.status),
        preview: '',
      },
      {
        id: 'requests.priority',
        source: 'requests',
        key: 'priority',
        label: 'Request Priority',
        description: 'Request priority level',
        sample: findFirstValue(requestsData, item => item.priority),
        preview: '',
      },
      {
        id: 'requests.department_id',
        source: 'requests',
        key: 'department_id',
        label: 'Department ID',
        description: 'Department linked to request',
        sample: findFirstValue(requestsData, item => item.department_id),
        preview: '',
      },
      {
        id: 'requests.assignee_name',
        source: 'requests',
        key: 'assignee_name',
        label: 'Assignee Name',
        description: 'Current assignee full name',
        sample: findFirstValue(requestsData, item => item.assignee?.full_name),
        preview: '',
      },
      {
        id: 'requests.created_at',
        source: 'requests',
        key: 'created_at',
        label: 'Created At',
        description: 'Request creation timestamp',
        sample: findFirstValue(requestsData, item => formatDateText(item.created_at)),
        preview: '',
      },
      {
        id: 'requests.description',
        source: 'requests',
        key: 'description',
        label: 'Description',
        description: 'Request description text',
        sample: findFirstValue(requestsData, item => item.description),
        preview: '',
      },
    ]

    const userFields: PaletteField[] = [
      {
        id: 'users.full_name',
        source: 'users',
        key: 'full_name',
        label: 'User Name',
        description: 'Employee full name',
        sample: findFirstValue(usersData, item => item.full_name),
        preview: '',
      },
      {
        id: 'users.email',
        source: 'users',
        key: 'email',
        label: 'User Email',
        description: 'Employee email address',
        sample: findFirstValue(usersData, item => item.email),
        preview: '',
      },
      {
        id: 'users.role',
        source: 'users',
        key: 'role',
        label: 'User Role',
        description: 'Employee role in CRM',
        sample: findFirstValue(usersData, item => item.role),
        preview: '',
      },
      {
        id: 'users.is_active',
        source: 'users',
        key: 'is_active',
        label: 'User Active',
        description: 'Whether user account is active',
        sample: findFirstValue(usersData, item => (typeof item.is_active === 'boolean' ? (item.is_active ? 'true' : 'false') : '')),
        preview: '',
      },
      {
        id: 'users.department_id',
        source: 'users',
        key: 'department_id',
        label: 'User Department ID',
        description: 'Department assigned to user',
        sample: findFirstValue(usersData, item => item.department_id),
        preview: '',
      },
    ]

    const clientFields: PaletteField[] = [
      {
        id: 'clients.full_name',
        source: 'clients',
        key: 'full_name',
        label: 'Client Name',
        description: 'Client first + last name',
        sample: findFirstValue(clientsData, item => `${item.first_name || ''} ${item.last_name || ''}`.trim()),
        preview: '',
      },
      {
        id: 'clients.email',
        source: 'clients',
        key: 'email',
        label: 'Client Email',
        description: 'Client email address',
        sample: findFirstValue(clientsData, item => item.email),
        preview: '',
      },
      {
        id: 'clients.phone',
        source: 'clients',
        key: 'phone',
        label: 'Client Phone',
        description: 'Client phone number',
        sample: findFirstValue(clientsData, item => item.phone),
        preview: '',
      },
      {
        id: 'clients.company_name',
        source: 'clients',
        key: 'company_name',
        label: 'Client Company',
        description: 'Linked company name',
        sample: findFirstValue(clientsData, item => item.company_name),
        preview: '',
      },
      {
        id: 'clients.status',
        source: 'clients',
        key: 'status',
        label: 'Client Status',
        description: 'Client status label',
        sample: findFirstValue(clientsData, item => item.status_label || item.status),
        preview: '',
      },
    ]

    const companyFields: PaletteField[] = [
      {
        id: 'companies.name',
        source: 'companies',
        key: 'name',
        label: 'Company Name',
        description: 'Registered company name',
        sample: findFirstValue(companiesData, item => item.name),
        preview: '',
      },
      {
        id: 'companies.registration_number',
        source: 'companies',
        key: 'registration_number',
        label: 'Registration Number',
        description: 'Company registration number',
        sample: findFirstValue(companiesData, item => item.registration_number),
        preview: '',
      },
      {
        id: 'companies.email',
        source: 'companies',
        key: 'email',
        label: 'Company Email',
        description: 'Company email',
        sample: findFirstValue(companiesData, item => item.email),
        preview: '',
      },
      {
        id: 'companies.phone',
        source: 'companies',
        key: 'phone',
        label: 'Company Phone',
        description: 'Company phone number',
        sample: findFirstValue(companiesData, item => item.phone),
        preview: '',
      },
      {
        id: 'companies.address',
        source: 'companies',
        key: 'address',
        label: 'Company Address',
        description: 'Company legal address',
        sample: findFirstValue(companiesData, item => item.address),
        preview: '',
      },
    ]

    const query = paletteSearch.trim().toLowerCase()

    const withPreview = (fields: PaletteField[]) =>
      fields
        .map(field => ({ ...field, preview: formatPreview(field.sample) }))
        .filter(field => {
          if (!query) return true
          return (
            field.label.toLowerCase().includes(query) ||
            field.key.toLowerCase().includes(query) ||
            field.description.toLowerCase().includes(query)
          )
        })

    return [
      {
        source: 'requests' as ObjectSource,
        label: 'Requests',
        fields: withPreview(requestFields),
      },
      {
        source: 'users' as ObjectSource,
        label: 'Users',
        fields: withPreview(userFields),
      },
      {
        source: 'clients' as ObjectSource,
        label: 'Clients',
        fields: withPreview(clientFields),
      },
      {
        source: 'companies' as ObjectSource,
        label: 'Companies',
        fields: withPreview(companyFields),
      },
    ]
  }, [requestsData, usersData, clientsData, companiesData, paletteSearch])

  const safeSelectedCell = useMemo(() => normalizeCellPosition(selectedCell), [selectedCell])
  const selectedCellData = grid[safeSelectedCell.row]?.[safeSelectedCell.col] || buildEmptyCell()
  const fillRange = useMemo(() => {
    if (!fillDragState) return null
    return getFillRange(fillDragState.source, fillDragState.end)
  }, [fillDragState])

  const derivedColumns = useMemo(() => {
    const columns: ReportTypeColumn[] = []
    const usedKeys = new Set<string>()

    for (let col = 0; col < GRID_COLS; col += 1) {
      const headerCell = grid[0]?.[col]
      const headerLabel = headerCell?.value?.trim() || ''

      let binding: ColumnBinding | null = null
      for (let row = 0; row < GRID_ROWS; row += 1) {
        const maybeBinding = grid[row]?.[col]?.binding
        if (maybeBinding) {
          binding = maybeBinding
          break
        }
      }

      if (!headerLabel && !binding) continue

      const columnLabel = headerLabel || binding?.label || `Column ${getColumnLabel(col)}`
      const fallbackKey = `column_${getColumnLabel(col).toLowerCase()}`
      const baseKey = toSafeKey(binding?.key || columnLabel, fallbackKey)

      let uniqueKey = baseKey
      let keyIndex = 2
      while (usedKeys.has(uniqueKey.toLowerCase())) {
        uniqueKey = `${baseKey}_${keyIndex}`
        keyIndex += 1
      }
      usedKeys.add(uniqueKey.toLowerCase())

      columns.push({
        key: uniqueKey,
        label: columnLabel,
        formula: binding ? `${binding.source}.${binding.key}` : null,
        format: null,
      })
    }

    return columns
  }, [grid])

  const spreadsheetSources = useMemo(() => {
    const sources = new Set<ObjectSource>()
    grid.forEach(row => {
      row.forEach(cell => {
        if (cell.binding?.source && isObjectSource(cell.binding.source)) {
          sources.add(cell.binding.source)
        }
      })
    })
    return Array.from(sources)
  }, [grid])

  const applyCellsInRange = (
    range: FillRange,
    updater: (cell: SpreadsheetCell, row: number, col: number) => SpreadsheetCell,
  ) => {
    setGrid(prev => {
      const next = cloneGrid(prev)
      for (let row = range.minRow; row <= range.maxRow; row += 1) {
        for (let col = range.minCol; col <= range.maxCol; col += 1) {
          next[row][col] = updater(next[row][col], row, col)
        }
      }
      return next
    })
  }

  const updateSelectedCellStyle = (patch: Partial<Omit<CellStyle, 'borders'>> & { borders?: Partial<CellBorders> }) => {
    const target = normalizeCellPosition(safeSelectedCell)
    setGrid(prev => {
      if (!prev[target.row]?.[target.col]) return prev
      const next = cloneGrid(prev)
      const current = next[target.row][target.col]
      next[target.row][target.col] = {
        ...current,
        style: {
          ...current.style,
          ...patch,
          borders: patch.borders
            ? {
                ...current.style.borders,
                ...patch.borders,
              }
            : { ...current.style.borders },
        },
      }
      return next
    })
  }

  const applyFillRange = () => {
    if (!fillDragState) return
    const source = normalizeCellPosition(fillDragState.source)
    const targetRange = getFillRange(source, fillDragState.end)

    setGrid(prev => {
      if (!prev[source.row]?.[source.col]) return prev
      const sourceCell = prev[source.row][source.col]
      const next = cloneGrid(prev)

      for (let row = targetRange.minRow; row <= targetRange.maxRow; row += 1) {
        for (let col = targetRange.minCol; col <= targetRange.maxCol; col += 1) {
          if (row === source.row && col === source.col) continue
          next[row][col] = {
            ...next[row][col],
            value: sourceCell.value,
            binding: sourceCell.binding ? { ...sourceCell.binding } : null,
            style: cloneCellStyle(sourceCell.style),
          }
          if (row !== 0 && !next[0][col].value.trim() && sourceCell.binding) {
            next[0][col].value = sourceCell.binding.label
            next[0][col].binding = null
          }
        }
      }
      return next
    })

    setSelectedCell(normalizeCellPosition(fillDragState.end))
    setFillDragState(null)
  }

  useEffect(() => {
    if (!fillDragState) return

    const onMouseUp = () => {
      applyFillRange()
    }

    window.addEventListener('mouseup', onMouseUp)
    return () => window.removeEventListener('mouseup', onMouseUp)
  }, [fillDragState])

  const getCellBorderStyle = (cell: SpreadsheetCell) => ({
    borderTop: `1px solid ${cell.style.borders.top ? CUSTOM_CELL_BORDER_COLOR : DEFAULT_CELL_BORDER_COLOR}`,
    borderRight: `1px solid ${cell.style.borders.right ? CUSTOM_CELL_BORDER_COLOR : DEFAULT_CELL_BORDER_COLOR}`,
    borderBottom: `1px solid ${cell.style.borders.bottom ? CUSTOM_CELL_BORDER_COLOR : DEFAULT_CELL_BORDER_COLOR}`,
    borderLeft: `1px solid ${cell.style.borders.left ? CUSTOM_CELL_BORDER_COLOR : DEFAULT_CELL_BORDER_COLOR}`,
  })

  const applyBorderPreset = (preset: 'all' | 'none' | 'outline') => {
    const range = fillRange || getFillRange(safeSelectedCell, safeSelectedCell)
    applyCellsInRange(range, (cell, row, col) => {
      if (preset === 'none') {
        return {
          ...cell,
          style: {
            ...cell.style,
            borders: {
              top: false,
              right: false,
              bottom: false,
              left: false,
            },
          },
        }
      }

      if (preset === 'all') {
        return {
          ...cell,
          style: {
            ...cell.style,
            borders: {
              top: true,
              right: true,
              bottom: true,
              left: true,
            },
          },
        }
      }

      return {
        ...cell,
        style: {
          ...cell.style,
          borders: {
            top: row === range.minRow,
            right: col === range.maxCol,
            bottom: row === range.maxRow,
            left: col === range.minCol,
          },
        },
      }
    })
  }

  const clearSelectedCellFormatting = () => {
    updateSelectedCellStyle({
      fillColor: null,
      textColor: null,
      bold: false,
      italic: false,
      align: 'left',
      borders: {
        top: false,
        right: false,
        bottom: false,
        left: false,
      },
    })
  }

  const insertQuickFormula = (formulaType: 'SUM' | 'AVERAGE' | 'COUNT') => {
    const colLabel = getColumnLabel(safeSelectedCell.col)
    const formula = `=${formulaType}(${colLabel}2:${colLabel}${GRID_ROWS})`
    updateCellValue(safeSelectedCell.row, safeSelectedCell.col, formula)
  }

  const insertNowValue = () => {
    updateCellValue(
      safeSelectedCell.row,
      safeSelectedCell.col,
      new Date().toLocaleString(),
    )
  }

  const clearSpreadsheet = () => {
    setGrid(buildEmptyGrid())
    setSelectedCell({ row: 0, col: 0 })
    setFillDragState(null)
  }

  const updateCellValue = (row: number, col: number, value: string) => {
    setGrid(prev => {
      if (!prev[row]?.[col]) return prev
      const next = cloneGrid(prev)
      next[row][col].value = value
      if (!value.trim()) {
        next[row][col].binding = null
      }
      return next
    })
  }

  const applyFieldToCell = (field: PaletteField, row: number, col: number) => {
    const sampleValue = field.sample || `[${field.source}.${field.key}]`
    setGrid(prev => {
      if (!prev[row]?.[col]) return prev
      const next = cloneGrid(prev)
      const currentStyle = cloneCellStyle(next[row][col].style)
      next[row][col] = {
        value: sampleValue,
        binding: {
          source: field.source,
          key: field.key,
          label: field.label,
        },
        style: currentStyle,
      }

      if (row !== 0 && !next[0][col].value.trim()) {
        next[0][col].value = field.label
        next[0][col].binding = null
      }

      if (row === 0 && next[1]?.[col] && !next[1][col].value.trim()) {
        const copiedStyle = cloneCellStyle(next[1][col].style)
        next[1][col] = {
          value: sampleValue,
          binding: {
            source: field.source,
            key: field.key,
            label: field.label,
          },
          style: copiedStyle,
        }
      }

      return next
    })
    setSelectedCell({ row, col })
  }

  const onFieldDragStart = (event: React.DragEvent<HTMLButtonElement>, field: PaletteField) => {
    event.dataTransfer.effectAllowed = 'copy'
    event.dataTransfer.setData(DRAG_FIELD_MIME, JSON.stringify(field))
    event.dataTransfer.setData('text/plain', `${field.source}.${field.key}`)
  }

  const onCellDrop = (event: React.DragEvent<HTMLTableCellElement>, row: number, col: number) => {
    event.preventDefault()
    const payload = event.dataTransfer.getData(DRAG_FIELD_MIME)
    if (!payload) return

    try {
      const parsed = JSON.parse(payload) as Partial<PaletteField>
      if (!parsed || typeof parsed.key !== 'string' || typeof parsed.label !== 'string' || typeof parsed.source !== 'string') {
        return
      }
      if (!isObjectSource(parsed.source)) return

      const field: PaletteField = {
        id: typeof parsed.id === 'string' ? parsed.id : `${parsed.source}.${parsed.key}`,
        source: parsed.source,
        key: parsed.key,
        label: parsed.label,
        description: typeof parsed.description === 'string' ? parsed.description : '',
        sample: typeof parsed.sample === 'string' ? parsed.sample : '',
        preview: typeof parsed.preview === 'string' ? parsed.preview : formatPreview(typeof parsed.sample === 'string' ? parsed.sample : ''),
      }

      applyFieldToCell(field, row, col)
    } catch {
      // Ignore malformed drag payloads.
    }
  }

  const startFillDrag = (event: React.MouseEvent, row: number, col: number) => {
    event.preventDefault()
    event.stopPropagation()
    setFillDragState({
      source: normalizeCellPosition({ row, col }),
      end: normalizeCellPosition({ row, col }),
    })
  }

  const onCellMouseEnter = (row: number, col: number) => {
    if (!fillDragState) return
    setFillDragState(prev => {
      if (!prev) return prev
      return {
        ...prev,
        end: normalizeCellPosition({ row, col }),
      }
    })
  }

  const isCellInsideFillRange = (row: number, col: number) => {
    if (!fillRange) return false
    return (
      row >= fillRange.minRow &&
      row <= fillRange.maxRow &&
      col >= fillRange.minCol &&
      col <= fillRange.maxCol
    )
  }

  const openCreateGuide = (reason: 'default' | 'name' | 'columns' | 'source-mismatch') => {
    if (reason === 'name') {
      setGuideModal({
        title: 'Report Name Is Missing',
        message: 'Add a clear name before creating the report type.',
        steps: [
          'Enter a report type name with at least 2 characters.',
          'Example: "Requests by Department" or "Active Clients Weekly".',
          'Then click "Create report type" again.',
        ],
      })
      return
    }

    if (reason === 'columns') {
      setGuideModal({
        title: 'No Spreadsheet Columns Detected',
        message: 'The report needs at least one configured column.',
        steps: [
          'Type a column header in the first row (A1, B1, ...), or',
          'Drag an object block from the right panel into any cell.',
          'Confirm "Columns detected" is at least 1, then create the report.',
        ],
      })
      return
    }

    if (reason === 'source-mismatch') {
      setGuideModal({
        title: 'Multiple Object Groups Detected',
        message: 'Your sheet uses fields from multiple object sources.',
        steps: [
          'Set source to "Custom dataset" in the source dropdown.',
          'Or keep a single object source (only Requests, only Users, etc.).',
          'Save after source and dragged fields are consistent.',
        ],
      })
      return
    }

    setGuideModal({
      title: 'How To Create A Report Type',
      message: 'Quick checklist for successful creation.',
      steps: [
        '1) Enter report name and select source.',
        '2) Fill the sheet: headers in row 1 and/or drag object blocks.',
        '3) Ensure "Columns detected" is greater than 0.',
        '4) Click "Create report type".',
      ],
    })
  }

  const handleImportFromFile = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!currentUser) return

    const token = readToken()
    if (!token) return

    if (!fileImportForm.file) {
      setError('Select a CSV or XLSX file for import.')
      return
    }

    const reportName = fileImportForm.name.trim()
    if (reportName.length < 2) {
      setError('Imported report type name must be at least 2 characters.')
      return
    }

    const headerRow = Math.min(Math.max(Number(fileImportForm.header_row) || 1, 1), 100)
    setImportingFile(true)
    setError(null)
    setNotice(null)

    try {
      const payload = new FormData()
      payload.append('file', fileImportForm.file)
      payload.append('name', reportName)
      payload.append('description', fileImportForm.description.trim())
      payload.append('is_active', String(fileImportForm.is_active))
      payload.append('header_row', String(headerRow))
      if (fileImportForm.worksheet_name.trim()) {
        payload.append('worksheet_name', fileImportForm.worksheet_name.trim())
      }
      if (fileImportForm.source !== 'auto') {
        payload.append('source', fileImportForm.source)
      }

      await axios.post('/reports/types/import-file', payload, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams(currentUser),
      })

      setNotice('Template imported from file.')
      setFileImportForm({
        file: null,
        name: '',
        description: '',
        source: 'auto',
        is_active: true,
        header_row: 1,
        worksheet_name: '',
      })
      setFileInputResetKey(prev => prev + 1)
      await fetchReportTypes(currentUser)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        handleUnauthorized()
        return
      }
      setError(err?.response?.data?.detail || 'Failed to import template from file')
    } finally {
      setImportingFile(false)
    }
  }

  const handleImportFromGoogle = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!currentUser) return

    const token = readToken()
    if (!token) return

    const reportName = googleImportForm.name.trim()
    if (reportName.length < 2) {
      setError('Google import report name must be at least 2 characters.')
      return
    }
    if (!googleImportForm.google_sheet_url.trim()) {
      setError('Google Sheets URL is required.')
      return
    }

    const headerRow = Math.min(Math.max(Number(googleImportForm.header_row) || 1, 1), 100)
    setImportingGoogle(true)
    setError(null)
    setNotice(null)

    try {
      await axios.post(
        '/reports/types/import-google',
        {
          name: reportName,
          google_sheet_url: googleImportForm.google_sheet_url.trim(),
          description: googleImportForm.description.trim() || null,
          source: googleImportForm.source === 'auto' ? undefined : googleImportForm.source,
          is_active: googleImportForm.is_active,
          header_row: headerRow,
          worksheet_gid: googleImportForm.worksheet_gid.trim() || null,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: getWorkspaceParams(currentUser),
        },
      )

      setNotice('Template imported from Google Sheets.')
      setGoogleImportForm({
        name: '',
        google_sheet_url: '',
        description: '',
        source: 'auto',
        is_active: true,
        header_row: 1,
        worksheet_gid: '',
      })
      await fetchReportTypes(currentUser)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        handleUnauthorized()
        return
      }
      setError(err?.response?.data?.detail || 'Failed to import from Google Sheets')
    } finally {
      setImportingGoogle(false)
    }
  }

  const openEmbeddedGoogleEditor = () => {
    const sourceUrl = googleImportForm.google_sheet_url.trim()
    if (!sourceUrl) {
      setError('Google Sheets URL is required to open the embedded editor.')
      return
    }

    const embeddedUrl = toGoogleSheetEmbeddedEditorUrl(sourceUrl)
    if (!embeddedUrl) {
      setError('Invalid Google Sheets URL.')
      return
    }

    setError(null)
    setNotice(
      'Embedded Google editor opened. If Google blocks embedding for your account, use URL import or file upload.',
    )
    setEmbeddedGoogleEditorUrl(embeddedUrl)
  }

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!currentUser) return

    const token = readToken()
    if (!token) return

    const reportName = form.name.trim()
    if (reportName.length < 2) {
      setError('Report type name must be at least 2 characters.')
      openCreateGuide('name')
      return
    }

    if (derivedColumns.length === 0) {
      setError('Fill at least one spreadsheet column (header row or drag object blocks).')
      openCreateGuide('columns')
      return
    }

    if (spreadsheetSources.length > 1 && form.source !== 'custom') {
      setError('Spreadsheet contains multiple object groups. Set source to "Custom dataset" before saving.')
      openCreateGuide('source-mismatch')
      return
    }

    setSaving(true)
    setError(null)
    setNotice(null)
    setGuideModal(null)
    try {
      await axios.post(
        '/reports/types',
        {
          name: reportName,
          description: form.description.trim() || null,
          source: form.source,
          is_active: form.is_active,
          columns: derivedColumns,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: getWorkspaceParams(currentUser),
        },
      )

      setForm({
        name: '',
        description: '',
        source: 'requests',
        is_active: true,
      })
      clearSpreadsheet()
      setNotice('Report type created.')
      await fetchReportTypes(currentUser)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        handleUnauthorized()
        return
      }
      setError(err?.response?.data?.detail || 'Failed to create report type')
      openCreateGuide('default')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (reportTypeId: string) => {
    if (!currentUser) return
    if (!window.confirm('Delete this report type?')) return

    const token = readToken()
    if (!token) return

    setDeletingId(reportTypeId)
    setError(null)
    setNotice(null)
    try {
      await axios.delete(`/reports/types/${reportTypeId}`, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams(currentUser),
      })
      await fetchReportTypes(currentUser)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        handleUnauthorized()
        return
      }
      setError(err?.response?.data?.detail || 'Failed to delete report type')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return <div style={{ padding: theme.spacing.lg }}>Loading report types...</div>
  }

  if (!canManageReportTypes) {
    return (
      <div style={{ padding: theme.spacing.lg }}>
        <h2 style={{ marginTop: 0 }}>Report Types</h2>
        <div style={{ color: theme.colors.error }}>{error || 'Access denied'}</div>
      </div>
    )
  }

  return (
    <div className="crm-page-shell" style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.lg }}>
      <div className="crm-page-header">
        <div>
          <h2 style={{ margin: 0 }}>Report Types</h2>
          <div style={{ color: theme.colors.gray.text, fontSize: '13px' }}>
            Build report templates in spreadsheet mode. Drag object blocks into cells to auto-fill sample values.
          </div>
        </div>
        <button
          onClick={() => navigate('/reports')}
          style={{
            border: `1px solid ${theme.colors.gray.border}`,
            background: '#fff',
            borderRadius: theme.borderRadius.md,
            padding: '8px 12px',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          Back to Reports
        </button>
      </div>

      {error && (
        <div
          style={{
            border: '1px solid #ffa39e',
            background: '#fff1f0',
            color: '#cf1322',
            borderRadius: theme.borderRadius.md,
            padding: theme.spacing.md,
          }}
        >
          {error}
        </div>
      )}

      {notice && (
        <div
          style={{
            border: '1px solid #b7eb8f',
            background: '#f6ffed',
            color: '#237804',
            borderRadius: theme.borderRadius.md,
            padding: theme.spacing.md,
          }}
        >
          {notice}
        </div>
      )}

      {objectsWarning && (
        <div
          style={{
            border: '1px solid #ffe58f',
            background: '#fffbe6',
            color: '#ad6800',
            borderRadius: theme.borderRadius.md,
            padding: theme.spacing.md,
          }}
        >
          {objectsWarning}
        </div>
      )}

      {guideModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 160,
            background: 'rgba(15, 23, 42, 0.38)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: theme.spacing.md,
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '560px',
              background: '#fff',
              borderRadius: theme.borderRadius.lg,
              border: `1px solid ${theme.colors.gray.border}`,
              boxShadow: theme.shadows.lg,
              padding: theme.spacing.md,
              display: 'flex',
              flexDirection: 'column',
              gap: theme.spacing.sm,
            }}
          >
            <div style={{ fontSize: '18px', fontWeight: 700 }}>{guideModal.title}</div>
            <div style={{ fontSize: '13px', color: theme.colors.gray.text }}>{guideModal.message}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {guideModal.steps.map((item, index) => (
                <div key={`guide-step-${index}`} style={{ fontSize: '13px' }}>
                  {item}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setGuideModal(null)}
                style={{
                  border: `1px solid ${theme.colors.gray.border}`,
                  background: '#fff',
                  borderRadius: theme.borderRadius.sm,
                  padding: '8px 12px',
                  cursor: 'pointer',
                }}
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}

      <div
        style={{
          background: '#fff',
          borderRadius: theme.borderRadius.lg,
          boxShadow: theme.shadows.sm,
          padding: theme.spacing.md,
          display: 'flex',
          flexDirection: 'column',
          gap: theme.spacing.md,
        }}
      >
        <div>
          <h3 style={{ margin: 0 }}>Import Template (Add-On)</h3>
          <div style={{ color: theme.colors.gray.text, fontSize: '12px', marginTop: '4px' }}>
            Keep using the built-in editor below. These options create templates from existing files or a Google Sheet.
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
            gap: theme.spacing.md,
          }}
        >
          <form
            onSubmit={handleImportFromFile}
            style={{
              border: `1px solid ${theme.colors.gray.border}`,
              borderRadius: theme.borderRadius.md,
              padding: theme.spacing.sm,
              display: 'flex',
              flexDirection: 'column',
              gap: theme.spacing.sm,
            }}
          >
            <div style={{ fontWeight: 700 }}>Option 1: Upload CSV/XLSX</div>
            <input
              key={`report-template-file-${fileInputResetKey}`}
              type="file"
              accept=".csv,.xlsx,.xlsm,.xltx,.xltm"
              onChange={event => setFileImportForm(prev => ({ ...prev, file: event.target.files?.[0] || null }))}
              required
            />
            <input
              required
              placeholder="Template name"
              value={fileImportForm.name}
              onChange={event => setFileImportForm(prev => ({ ...prev, name: event.target.value }))}
              style={{ width: '100%', padding: '8px' }}
            />
            <textarea
              placeholder="Description (optional)"
              rows={2}
              value={fileImportForm.description}
              onChange={event => setFileImportForm(prev => ({ ...prev, description: event.target.value }))}
              style={{ width: '100%', padding: '8px', resize: 'vertical' }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 110px', gap: theme.spacing.xs }}>
              <select
                value={fileImportForm.source}
                onChange={event => setFileImportForm(prev => ({ ...prev, source: event.target.value as ImportSourceSelection }))}
                style={{ width: '100%', padding: '8px' }}
              >
                {IMPORT_SOURCE_OPTIONS.map(option => (
                  <option key={`file-import-source-${option.value}`} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                max={100}
                value={fileImportForm.header_row}
                onChange={event => setFileImportForm(prev => ({ ...prev, header_row: Number(event.target.value) || 1 }))}
                placeholder="Header row"
                title="Header row"
                style={{ width: '100%', padding: '8px' }}
              />
            </div>
            <input
              placeholder="Worksheet name (optional for XLSX)"
              value={fileImportForm.worksheet_name}
              onChange={event => setFileImportForm(prev => ({ ...prev, worksheet_name: event.target.value }))}
              style={{ width: '100%', padding: '8px' }}
            />
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
              <input
                type="checkbox"
                checked={fileImportForm.is_active}
                onChange={event => setFileImportForm(prev => ({ ...prev, is_active: event.target.checked }))}
              />
              Active
            </label>
            <button
              type="submit"
              disabled={importingFile}
              style={{
                border: 'none',
                background: theme.colors.primary,
                color: '#fff',
                borderRadius: theme.borderRadius.sm,
                padding: '8px 12px',
                cursor: importingFile ? 'not-allowed' : 'pointer',
              }}
            >
              {importingFile ? 'Importing...' : 'Import file template'}
            </button>
          </form>

          <form
            onSubmit={handleImportFromGoogle}
            style={{
              border: `1px solid ${theme.colors.gray.border}`,
              borderRadius: theme.borderRadius.md,
              padding: theme.spacing.sm,
              display: 'flex',
              flexDirection: 'column',
              gap: theme.spacing.sm,
            }}
          >
            <div style={{ fontWeight: 700 }}>Option 2: Import Google Sheet</div>
            <input
              required
              placeholder="Template name"
              value={googleImportForm.name}
              onChange={event => setGoogleImportForm(prev => ({ ...prev, name: event.target.value }))}
              style={{ width: '100%', padding: '8px' }}
            />
            <input
              required
              placeholder="Google Sheets URL"
              value={googleImportForm.google_sheet_url}
              onChange={event => setGoogleImportForm(prev => ({ ...prev, google_sheet_url: event.target.value }))}
              style={{ width: '100%', padding: '8px' }}
            />
            <button
              type="button"
              onClick={openEmbeddedGoogleEditor}
              style={{
                border: `1px solid ${theme.colors.gray.border}`,
                background: '#fff',
                color: '#1f2937',
                borderRadius: theme.borderRadius.sm,
                padding: '8px 12px',
                cursor: 'pointer',
              }}
            >
              Open embedded editor
            </button>
            <textarea
              placeholder="Description (optional)"
              rows={2}
              value={googleImportForm.description}
              onChange={event => setGoogleImportForm(prev => ({ ...prev, description: event.target.value }))}
              style={{ width: '100%', padding: '8px', resize: 'vertical' }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 110px', gap: theme.spacing.xs }}>
              <select
                value={googleImportForm.source}
                onChange={event => setGoogleImportForm(prev => ({ ...prev, source: event.target.value as ImportSourceSelection }))}
                style={{ width: '100%', padding: '8px' }}
              >
                {IMPORT_SOURCE_OPTIONS.map(option => (
                  <option key={`google-import-source-${option.value}`} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                max={100}
                value={googleImportForm.header_row}
                onChange={event => setGoogleImportForm(prev => ({ ...prev, header_row: Number(event.target.value) || 1 }))}
                placeholder="Header row"
                title="Header row"
                style={{ width: '100%', padding: '8px' }}
              />
            </div>
            <input
              placeholder="Worksheet GID (optional)"
              value={googleImportForm.worksheet_gid}
              onChange={event => setGoogleImportForm(prev => ({ ...prev, worksheet_gid: event.target.value }))}
              style={{ width: '100%', padding: '8px' }}
            />
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
              <input
                type="checkbox"
                checked={googleImportForm.is_active}
                onChange={event => setGoogleImportForm(prev => ({ ...prev, is_active: event.target.checked }))}
              />
              Active
            </label>
            <button
              type="submit"
              disabled={importingGoogle}
              style={{
                border: 'none',
                background: '#0f766e',
                color: '#fff',
                borderRadius: theme.borderRadius.sm,
                padding: '8px 12px',
                cursor: importingGoogle ? 'not-allowed' : 'pointer',
              }}
            >
              {importingGoogle ? 'Importing...' : 'Import Google template'}
            </button>
          </form>
        </div>
      </div>

      <form
        onSubmit={handleCreate}
        style={{
          background: '#fff',
          borderRadius: theme.borderRadius.lg,
          boxShadow: theme.shadows.sm,
          padding: theme.spacing.md,
          display: 'flex',
          flexDirection: 'column',
          gap: theme.spacing.md,
          minWidth: 0,
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr',
            gap: theme.spacing.sm,
          }}
        >
          <input
            required
            placeholder="Report type name"
            value={form.name}
            onChange={event => setForm(prev => ({ ...prev, name: event.target.value }))}
            style={{ width: '100%', padding: '8px' }}
          />
          <select
            value={form.source}
            onChange={event => setForm(prev => ({ ...prev, source: event.target.value as ReportSource }))}
            style={{ width: '100%', padding: '8px' }}
          >
            {SOURCE_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <textarea
          placeholder="Description (optional)"
          rows={2}
          value={form.description}
          onChange={event => setForm(prev => ({ ...prev, description: event.target.value }))}
          style={{ width: '100%', padding: '8px', resize: 'vertical' }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: theme.spacing.xs,
            }}
          >
            <div style={{ fontSize: '12px', color: theme.colors.gray.text }}>
              Spreadsheet tools: formatting, borders, fill handle, quick formulas.
            </div>
            <div style={{ display: 'flex', gap: theme.spacing.xs, alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => openCreateGuide('default')}
                style={{
                  border: `1px solid ${theme.colors.gray.border}`,
                  background: '#fff',
                  borderRadius: theme.borderRadius.sm,
                  padding: '7px 10px',
                  cursor: 'pointer',
                }}
              >
                Creation Help
              </button>
              <button
                type="button"
                onClick={() => setIsSpreadsheetFullscreen(prev => !prev)}
                style={{
                  border: `1px solid ${theme.colors.gray.border}`,
                  background: '#fff',
                  borderRadius: theme.borderRadius.sm,
                  padding: '7px 10px',
                  cursor: 'pointer',
                }}
              >
                {isSpreadsheetFullscreen ? 'Exit Full Window' : 'Open Full Window'}
              </button>
            </div>
          </div>

          <div
            style={
              isSpreadsheetFullscreen
                ? {
                    position: 'fixed',
                    inset: 0,
                    zIndex: 100,
                    background: '#f5f7fb',
                    padding: theme.spacing.md,
                    overflow: 'auto',
                  }
                : undefined
            }
          >
            <div
              style={{
                background: '#fff',
                border: `1px solid ${theme.colors.gray.border}`,
                borderRadius: theme.borderRadius.md,
                padding: theme.spacing.sm,
                boxShadow: isSpreadsheetFullscreen ? theme.shadows.md : 'none',
                minHeight: isSpreadsheetFullscreen ? 'calc(100vh - 32px)' : undefined,
                display: 'flex',
                flexDirection: 'column',
                gap: theme.spacing.sm,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: theme.spacing.xs,
                  alignItems: 'center',
                  border: `1px solid ${theme.colors.gray.border}`,
                  borderRadius: theme.borderRadius.sm,
                  padding: '6px',
                  background: '#f8fafc',
                  position: isSpreadsheetFullscreen ? 'sticky' : 'static',
                  top: isSpreadsheetFullscreen ? 0 : undefined,
                  zIndex: isSpreadsheetFullscreen ? 5 : undefined,
                }}
              >
                <button
                  type="button"
                  onClick={() => updateSelectedCellStyle({ bold: !selectedCellData.style.bold })}
                  style={toolbarButton(selectedCellData.style.bold)}
                >
                  B
                </button>
                <button
                  type="button"
                  onClick={() => updateSelectedCellStyle({ italic: !selectedCellData.style.italic })}
                  style={{ ...toolbarButton(selectedCellData.style.italic), fontStyle: 'italic' }}
                >
                  I
                </button>
                <select
                  value={selectedCellData.style.align}
                  onChange={event => updateSelectedCellStyle({ align: event.target.value as CellStyle['align'] })}
                  style={toolbarSelect}
                >
                  <option value="left">Align Left</option>
                  <option value="center">Align Center</option>
                  <option value="right">Align Right</option>
                </select>
                <label style={toolbarColorLabel}>
                  Fill
                  <input
                    type="color"
                    value={selectedCellData.style.fillColor || '#ffffff'}
                    onChange={event => updateSelectedCellStyle({ fillColor: event.target.value })}
                    style={toolbarColorInput}
                  />
                </label>
                <label style={toolbarColorLabel}>
                  Text
                  <input
                    type="color"
                    value={selectedCellData.style.textColor || '#111827'}
                    onChange={event => updateSelectedCellStyle({ textColor: event.target.value })}
                    style={toolbarColorInput}
                  />
                </label>
                <button type="button" onClick={() => applyBorderPreset('all')} style={toolbarButton()}>
                  Border All
                </button>
                <button type="button" onClick={() => applyBorderPreset('outline')} style={toolbarButton()}>
                  Border Outer
                </button>
                <button type="button" onClick={() => applyBorderPreset('none')} style={toolbarButton()}>
                  Border None
                </button>
                <button type="button" onClick={() => insertQuickFormula('SUM')} style={toolbarButton()}>
                  fx SUM
                </button>
                <button type="button" onClick={() => insertQuickFormula('AVERAGE')} style={toolbarButton()}>
                  fx AVG
                </button>
                <button type="button" onClick={() => insertQuickFormula('COUNT')} style={toolbarButton()}>
                  fx COUNT
                </button>
                <button type="button" onClick={insertNowValue} style={toolbarButton()}>
                  Insert NOW
                </button>
                <button type="button" onClick={clearSelectedCellFormatting} style={toolbarButton()}>
                  Clear Format
                </button>
      </div>

      {embeddedGoogleEditorUrl && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 120,
            background: '#f5f7fb',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              padding: theme.spacing.sm,
              background: '#fff',
              borderBottom: `1px solid ${theme.colors.gray.border}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: theme.spacing.sm,
            }}
          >
            <div style={{ fontWeight: 700, fontSize: '13px' }}>Google Sheets Editor</div>
            <button
              type="button"
              onClick={() => setEmbeddedGoogleEditorUrl(null)}
              style={{
                border: `1px solid ${theme.colors.gray.border}`,
                background: '#fff',
                borderRadius: theme.borderRadius.sm,
                padding: '8px 12px',
                cursor: 'pointer',
              }}
            >
              Close full window
            </button>
          </div>
          <iframe
            src={embeddedGoogleEditorUrl}
            title="Embedded Google Sheets editor"
            style={{ border: 'none', width: '100%', height: '100%' }}
          />
        </div>
      )}

      <div
        style={{
                  display: 'grid',
                  gridTemplateColumns: isMobile && !isSpreadsheetFullscreen ? '1fr' : 'minmax(0, 1fr) 300px',
                  gap: theme.spacing.md,
                  alignItems: 'start',
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      border: `1px solid ${theme.colors.gray.border}`,
                      borderRadius: theme.borderRadius.md,
                      overflow: 'hidden',
                      marginBottom: theme.spacing.sm,
                    }}
                  >
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '84px minmax(0, 1fr)',
                        background: '#f4f6fb',
                        borderBottom: `1px solid ${theme.colors.gray.border}`,
                      }}
                    >
                      <div
                        style={{
                          borderRight: `1px solid ${theme.colors.gray.border}`,
                          padding: '8px 10px',
                          fontWeight: 700,
                          color: theme.colors.gray.text,
                          fontSize: '12px',
                        }}
                      >
                        {`${getColumnLabel(safeSelectedCell.col)}${safeSelectedCell.row + 1}`}
                      </div>
                      <input
                        value={selectedCellData.value}
                        onChange={event => updateCellValue(safeSelectedCell.row, safeSelectedCell.col, event.target.value)}
                        placeholder="Type a value or drop an object block"
                        style={{
                          width: '100%',
                          border: 'none',
                          outline: 'none',
                          padding: '8px 10px',
                          fontSize: '13px',
                          background: '#fff',
                          color: selectedCellData.style.textColor || '#111827',
                          fontWeight: selectedCellData.style.bold ? 700 : 400,
                          fontStyle: selectedCellData.style.italic ? 'italic' : 'normal',
                          textAlign: selectedCellData.style.align,
                        }}
                      />
                    </div>
                    <div
                      style={{
                        padding: '6px 10px',
                        fontSize: '12px',
                        color: selectedCellData.binding ? '#0f766e' : theme.colors.gray.text,
                        background: '#fff',
                      }}
                    >
                      {selectedCellData.binding
                        ? `Linked object: ${selectedCellData.binding.source}.${selectedCellData.binding.key}`
                        : 'Linked object: none'} | Fill handle: drag the square in bottom-right corner of selected cell.
                    </div>
                  </div>

                  <div
                    style={{
                      border: `1px solid ${theme.colors.gray.border}`,
                      borderRadius: theme.borderRadius.md,
                      overflow: 'auto',
                      maxHeight: isSpreadsheetFullscreen ? 'calc(100vh - 280px)' : '62vh',
                      background: '#fff',
                    }}
                  >
                    <table style={{ borderCollapse: 'separate', borderSpacing: 0, minWidth: `${(GRID_COLS + 1) * 150}px` }}>
                      <thead>
                        <tr>
                          <th
                            style={{
                              position: 'sticky',
                              top: 0,
                              left: 0,
                              zIndex: 3,
                              background: '#f3f4f6',
                              minWidth: '52px',
                              borderRight: `1px solid ${theme.colors.gray.border}`,
                              borderBottom: `1px solid ${theme.colors.gray.border}`,
                              height: '32px',
                            }}
                          />
                          {Array.from({ length: GRID_COLS }).map((_, colIndex) => (
                            <th
                              key={`col-header-${colIndex}`}
                              style={{
                                position: 'sticky',
                                top: 0,
                                zIndex: 2,
                                background: '#f3f4f6',
                                minWidth: '148px',
                                borderBottom: `1px solid ${theme.colors.gray.border}`,
                                borderRight: `1px solid ${theme.colors.gray.border}`,
                                padding: '6px 8px',
                                textAlign: 'center',
                                fontSize: '12px',
                                color: theme.colors.gray.text,
                              }}
                            >
                              {getColumnLabel(colIndex)}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {Array.from({ length: GRID_ROWS }).map((_, rowIndex) => (
                          <tr key={`row-${rowIndex}`}>
                            <th
                              style={{
                                position: 'sticky',
                                left: 0,
                                zIndex: 1,
                                background: '#f3f4f6',
                                width: '52px',
                                minWidth: '52px',
                                borderRight: `1px solid ${theme.colors.gray.border}`,
                                borderBottom: `1px solid ${theme.colors.gray.border}`,
                                padding: '0 8px',
                                textAlign: 'center',
                                fontSize: '12px',
                                color: theme.colors.gray.text,
                              }}
                            >
                              {rowIndex + 1}
                            </th>
                            {Array.from({ length: GRID_COLS }).map((_, colIndex) => {
                              const cell = grid[rowIndex][colIndex]
                              const isSelected = safeSelectedCell.row === rowIndex && safeSelectedCell.col === colIndex
                              const isInFillRange = isCellInsideFillRange(rowIndex, colIndex)
                              return (
                                <td
                                  key={`cell-${rowIndex}-${colIndex}`}
                                  onClick={() => setSelectedCell({ row: rowIndex, col: colIndex })}
                                  onMouseEnter={() => onCellMouseEnter(rowIndex, colIndex)}
                                  onDragOver={event => event.preventDefault()}
                                  onDrop={event => onCellDrop(event, rowIndex, colIndex)}
                                  style={{
                                    padding: 0,
                                    minWidth: '148px',
                                    background: '#fff',
                                    boxShadow: isInFillRange
                                      ? 'inset 0 0 0 2px #3b82f6'
                                      : undefined,
                                  }}
                                >
                                  <div
                                    style={{
                                      position: 'relative',
                                      ...getCellBorderStyle(cell),
                                      background: cell.style.fillColor || (isSelected ? '#eaf3ff' : cell.binding ? '#f0fdf4' : '#fff'),
                                    }}
                                  >
                                    <input
                                      value={cell.value}
                                      onFocus={() => setSelectedCell({ row: rowIndex, col: colIndex })}
                                      onChange={event => updateCellValue(rowIndex, colIndex, event.target.value)}
                                      style={{
                                        width: '100%',
                                        minHeight: '28px',
                                        padding: '5px 8px',
                                        fontSize: '12px',
                                        border: 'none',
                                        outline: 'none',
                                        background: 'transparent',
                                        color: cell.style.textColor || '#111827',
                                        fontWeight: cell.style.bold ? 700 : 400,
                                        fontStyle: cell.style.italic ? 'italic' : 'normal',
                                        textAlign: cell.style.align,
                                      }}
                                    />
                                    {isSelected && (
                                      <button
                                        type="button"
                                        onMouseDown={event => startFillDrag(event, rowIndex, colIndex)}
                                        style={{
                                          position: 'absolute',
                                          right: '-3px',
                                          bottom: '-3px',
                                          width: '8px',
                                          height: '8px',
                                          background: '#2563eb',
                                          border: 'none',
                                          borderRadius: '1px',
                                          cursor: 'crosshair',
                                          padding: 0,
                                        }}
                                        aria-label="Fill handle"
                                      />
                                    )}
                                  </div>
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div
                    style={{
                      marginTop: theme.spacing.sm,
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: theme.spacing.xs,
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div style={{ fontSize: '12px', color: theme.colors.gray.text }}>
                      Columns detected: <strong>{derivedColumns.length}</strong>
                      {spreadsheetSources.length > 0 && (
                        <span> | Objects used: {spreadsheetSources.join(', ')}</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: theme.spacing.xs, alignItems: 'center' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                        <input
                          type="checkbox"
                          checked={form.is_active}
                          onChange={event => setForm(prev => ({ ...prev, is_active: event.target.checked }))}
                        />
                        Active
                      </label>
                      <button
                        type="button"
                        onClick={clearSpreadsheet}
                        style={{
                          border: `1px solid ${theme.colors.gray.border}`,
                          background: '#fff',
                          borderRadius: theme.borderRadius.sm,
                          padding: '8px 10px',
                          cursor: 'pointer',
                        }}
                      >
                        Clear sheet
                      </button>
                      <button
                        type="submit"
                        disabled={saving}
                        style={{
                          border: 'none',
                          background: theme.colors.primary,
                          color: '#fff',
                          borderRadius: theme.borderRadius.sm,
                          padding: '8px 12px',
                          cursor: saving ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {saving ? 'Saving...' : 'Create report type'}
                      </button>
                    </div>
                  </div>
                </div>

                <aside
                  style={{
                    border: `1px solid ${theme.colors.gray.border}`,
                    borderRadius: theme.borderRadius.md,
                    padding: theme.spacing.sm,
                    background: '#fafafa',
                    maxHeight: isSpreadsheetFullscreen ? 'calc(100vh - 280px)' : '62vh',
                    overflow: 'auto',
                  }}
                >
                  <div style={{ marginBottom: theme.spacing.sm }}>
                    <div style={{ fontWeight: 700 }}>Object Blocks</div>
                    <div style={{ fontSize: '12px', color: theme.colors.gray.text }}>
                      Drag blocks into any row. Header row (top) is auto-filled when needed.
                    </div>
                  </div>

                  <input
                    value={paletteSearch}
                    onChange={event => setPaletteSearch(event.target.value)}
                    placeholder="Search object fields"
                    style={{ width: '100%', padding: '8px', marginBottom: theme.spacing.sm }}
                  />

                  {objectsLoading && (
                    <div style={{ fontSize: '12px', color: theme.colors.gray.text, marginBottom: theme.spacing.sm }}>
                      Loading object samples...
                    </div>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm }}>
                    {paletteGroups.map(group => {
                      const groupColor = SOURCE_COLORS[group.source]
                      return (
                        <div key={`palette-${group.source}`}>
                          <div
                            style={{
                              borderRadius: theme.borderRadius.sm,
                              background: groupColor.background,
                              color: groupColor.text,
                              padding: '6px 8px',
                              fontSize: '12px',
                              fontWeight: 700,
                              marginBottom: '6px',
                            }}
                          >
                            {group.label} ({group.fields.length})
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {group.fields.map(field => (
                              <button
                                key={field.id}
                                type="button"
                                draggable
                                onDragStart={event => onFieldDragStart(event, field)}
                                onClick={() => applyFieldToCell(field, safeSelectedCell.row, safeSelectedCell.col)}
                                style={{
                                  border: `1px solid ${groupColor.accent}`,
                                  background: groupColor.background,
                                  color: groupColor.text,
                                  borderRadius: theme.borderRadius.sm,
                                  padding: '8px',
                                  textAlign: 'left',
                                  cursor: 'grab',
                                }}
                                title={field.description}
                              >
                                <div style={{ fontSize: '12px', fontWeight: 700 }}>{field.label}</div>
                                <div style={{ fontSize: '11px', opacity: 0.86, marginTop: '2px' }}>
                                  {field.preview}
                                </div>
                              </button>
                            ))}
                            {group.fields.length === 0 && (
                              <div style={{ fontSize: '12px', color: theme.colors.gray.text, padding: '4px 2px' }}>
                                No fields match your search.
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </aside>
              </div>
            </div>
          </div>
        </div>
      </form>

      <div
        style={{
          background: '#fff',
          borderRadius: theme.borderRadius.lg,
          boxShadow: theme.shadows.sm,
          padding: theme.spacing.md,
          minWidth: 0,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Existing Report Types ({reportTypes.length})</h3>
        {reportTypes.length === 0 ? (
          <div style={{ color: theme.colors.gray.text }}>No report types created yet.</div>
        ) : (
          <div className="crm-table-scroll">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={tableHeader}>Name</th>
                  <th style={tableHeader}>Source</th>
                  <th style={tableHeader}>Columns</th>
                  <th style={tableHeader}>Status</th>
                  <th style={tableHeader}>Updated</th>
                  <th style={tableHeader}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reportTypes.map(item => (
                  <tr key={item.id}>
                    <td style={tableCell}>
                      <div style={{ fontWeight: 600 }}>{item.name}</div>
                      <div style={{ color: theme.colors.gray.text, fontSize: '12px' }}>{item.description || '—'}</div>
                    </td>
                    <td style={tableCell}>{item.source}</td>
                    <td style={tableCell}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {item.columns.slice(0, 3).map(column => (
                          <span key={`${item.id}-${column.key}`} style={{ fontSize: '12px' }}>
                            {column.label} ({column.key})
                          </span>
                        ))}
                        {item.columns.length > 3 && (
                          <span style={{ fontSize: '12px', color: theme.colors.gray.text }}>
                            +{item.columns.length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td style={tableCell}>{item.is_active ? 'Active' : 'Inactive'}</td>
                    <td style={tableCell}>{item.updated_at ? new Date(item.updated_at).toLocaleString() : '—'}</td>
                    <td style={tableCell}>
                      <button
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id}
                        style={{
                          border: '1px solid #ffa39e',
                          background: '#fff1f0',
                          color: '#cf1322',
                          borderRadius: theme.borderRadius.sm,
                          padding: '6px 10px',
                          cursor: deletingId === item.id ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {deletingId === item.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

const tableHeader = {
  borderBottom: '1px solid #ddd',
  textAlign: 'left' as const,
  padding: '8px',
  fontSize: '12px',
}

const toolbarButton = (active: boolean = false) => ({
  border: '1px solid #cbd5e1',
  background: active ? '#dbeafe' : '#fff',
  borderRadius: '4px',
  padding: '6px 8px',
  cursor: 'pointer',
  fontSize: '12px',
  fontWeight: 600,
})

const toolbarSelect = {
  border: '1px solid #cbd5e1',
  background: '#fff',
  borderRadius: '4px',
  padding: '6px 8px',
  cursor: 'pointer',
  fontSize: '12px',
}

const toolbarColorLabel = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  border: '1px solid #cbd5e1',
  background: '#fff',
  borderRadius: '4px',
  padding: '4px 6px',
  fontSize: '12px',
}

const toolbarColorInput = {
  width: '22px',
  height: '22px',
  border: 'none',
  background: 'transparent',
  padding: 0,
  cursor: 'pointer',
}

const tableCell = {
  borderBottom: '1px solid #f0f0f0',
  padding: '8px',
  fontSize: '13px',
  verticalAlign: 'top' as const,
  overflowWrap: 'anywhere' as const,
}

export default ReportTypesPage
