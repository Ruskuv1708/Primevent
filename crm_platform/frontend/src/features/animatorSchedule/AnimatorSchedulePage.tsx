import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from 'react'
import axios from 'axios'
import { getWorkspaceParams } from '../../shared/workspace'
import { useAppLayoutContext } from '../../shared/appLayoutContext'
import { roleMatches } from '../../shared/roleLabels'
import useIsMobile from '../../shared/useIsMobile'

type AnimatorOption = {
  id: string
  full_name: string
  email?: string
  role?: string
}

type AnimatorConflictBrief = {
  id: string
  event_type?: BookingEventType
  title: string
  client_name: string
  event_date: string
  start_time: string
  end_time: string
  program_name?: string
}

type AnimatorUnavailabilityBrief = {
  id: string
  animator_id: string
  unavailable_date: string
  start_time: string
  end_time: string
  duration_minutes: number
  reason: string
  notes?: string
}

type AnimatorAvailability = AnimatorOption & {
  is_available: boolean
  conflict_count: number
  conflicting_bookings: AnimatorConflictBrief[]
  conflicting_unavailability: AnimatorUnavailabilityBrief[]
}

type AnimatorBooking = {
  id: string
  event_type?: BookingEventType
  title: string
  client_name: string
  client_phone?: string
  event_date: string
  start_time: string
  end_time: string
  duration_minutes: number
  address?: string
  program_name?: string
  price?: number
  prepayment?: number
  payment_status?: string
  inventory_notes?: string
  status: string
  color: string
  notes?: string
  assigned_animators: AnimatorOption[]
  assigned_animator_ids: string[]
  parallel_count: number
  has_conflict: boolean
  conflict_animator_ids: string[]
  starts_at_minutes: number
  ends_at_minutes: number
}

type BookingFormState = {
  event_type: BookingEventType
  title: string
  client_name: string
  client_phone: string
  event_date: string
  start_time: string
  duration_minutes: string
  address: string
  program_name: string
  price: string
  prepayment: string
  payment_status: string
  inventory_notes: string
  assigned_animator_ids: string[]
  notes: string
}

type UnavailabilityItem = AnimatorUnavailabilityBrief & {
  animator?: AnimatorOption
}

type UnavailabilityFormState = {
  animator_id: string
  unavailable_date: string
  start_time: string
  duration_minutes: string
  reason: string
  notes: string
}

type BookingLayout = AnimatorBooking & {
  laneIndex: number
  laneCount: number
}

type BookingLayoutResult = {
  bookings: BookingLayout[]
  dayLaneCounts: Record<string, number>
}

type BookingEventType = 'order' | 'rehearsal'

const DAY_START_MINUTES = 8 * 60
const DAY_END_MINUTES = 22 * 60
const TIME_COLUMN_WIDTH = 64
const MOBILE_TIME_COLUMN_WIDTH = 48
const MIN_DAY_WIDTH = 300
const MIN_LANE_WIDTH = 220
const MOBILE_MIN_DAY_WIDTH = 148
const MOBILE_MIN_LANE_WIDTH = 108
const HOUR_HEIGHT = 120
const MOBILE_HOUR_HEIGHT = 76

const dateKey = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const startOfWeek = (date: Date) => {
  const next = new Date(date)
  const day = next.getDay() || 7
  next.setDate(next.getDate() - day + 1)
  next.setHours(0, 0, 0, 0)
  return next
}

const addDays = (date: Date, amount: number) => {
  const next = new Date(date)
  next.setDate(next.getDate() + amount)
  return next
}

const initialForm = (eventDate = dateKey(new Date())): BookingFormState => ({
  event_type: 'order',
  title: '',
  client_name: '',
  client_phone: '',
  event_date: eventDate,
  start_time: '10:00',
  duration_minutes: '60',
  address: '',
  program_name: '',
  price: '',
  prepayment: '',
  payment_status: 'pending',
  inventory_notes: '',
  assigned_animator_ids: [],
  notes: '',
})

const initialUnavailabilityForm = (eventDate = dateKey(new Date()), animatorId = ''): UnavailabilityFormState => ({
  animator_id: animatorId,
  unavailable_date: eventDate,
  start_time: '10:00',
  duration_minutes: '60',
  reason: '',
  notes: '',
})

const formFromBooking = (booking: AnimatorBooking): BookingFormState => ({
  event_type: booking.event_type || 'order',
  title: booking.title || '',
  client_name: booking.client_name || '',
  client_phone: booking.client_phone || '',
  event_date: booking.event_date,
  start_time: (booking.start_time || '10:00').slice(0, 5),
  duration_minutes: String(booking.duration_minutes || 60),
  address: booking.address || '',
  program_name: booking.program_name || '',
  price: booking.price != null ? String(booking.price) : '',
  prepayment: booking.prepayment != null ? String(booking.prepayment) : '',
  payment_status: booking.payment_status || 'pending',
  inventory_notes: booking.inventory_notes || '',
  assigned_animator_ids: booking.assigned_animator_ids || [],
  notes: booking.notes || '',
})

const getEventTypeLabel = (eventType: BookingEventType | undefined) => (
  eventType === 'rehearsal' ? 'Репетиция' : 'Заказ'
)

const getEventTypeActionLabel = (eventType: BookingEventType | undefined) => (
  eventType === 'rehearsal' ? 'репетицию' : 'заказ'
)

const layoutBookingGroup = (group: AnimatorBooking[]): BookingLayout[] => {
  const laneEnds: number[] = []
  const laneAssignments = new Map<string, number>()

  const ordered = [...group].sort((first, second) => {
    if (first.starts_at_minutes !== second.starts_at_minutes) {
      return first.starts_at_minutes - second.starts_at_minutes
    }
    return second.ends_at_minutes - first.ends_at_minutes
  })

  ordered.forEach(booking => {
    let laneIndex = laneEnds.findIndex(end => end <= booking.starts_at_minutes)
    if (laneIndex === -1) {
      laneIndex = laneEnds.length
      laneEnds.push(booking.ends_at_minutes)
    } else {
      laneEnds[laneIndex] = booking.ends_at_minutes
    }
    laneAssignments.set(booking.id, laneIndex)
  })

  const laneCount = Math.max(1, laneEnds.length)
  return ordered.map(booking => ({
    ...booking,
    laneIndex: laneAssignments.get(booking.id) || 0,
    laneCount,
  }))
}

const getBookingLayout = (bookings: AnimatorBooking[]): BookingLayoutResult => {
  const byDay = bookings.reduce<Record<string, AnimatorBooking[]>>((acc, booking) => {
    if (!acc[booking.event_date]) acc[booking.event_date] = []
    acc[booking.event_date].push(booking)
    return acc
  }, {})

  const dayLaneCounts: Record<string, number> = {}
  const laidOutBookings = Object.entries(byDay).flatMap(([dayKey, dayBookings]) => {
    const ordered = [...dayBookings].sort((first, second) => {
      if (first.starts_at_minutes !== second.starts_at_minutes) {
        return first.starts_at_minutes - second.starts_at_minutes
      }
      return second.ends_at_minutes - first.ends_at_minutes
    })
    const groups: AnimatorBooking[][] = []
    let currentGroup: AnimatorBooking[] = []
    let currentGroupEnd = 0

    ordered.forEach(booking => {
      if (!currentGroup.length || booking.starts_at_minutes < currentGroupEnd) {
        currentGroup.push(booking)
        currentGroupEnd = Math.max(currentGroupEnd, booking.ends_at_minutes)
        return
      }

      groups.push(currentGroup)
      currentGroup = [booking]
      currentGroupEnd = booking.ends_at_minutes
    })
    if (currentGroup.length) groups.push(currentGroup)

    const dayLayouts = groups.flatMap(layoutBookingGroup)
    dayLaneCounts[dayKey] = Math.max(1, ...dayLayouts.map(booking => booking.laneCount))
    return dayLayouts
  })

  return { bookings: laidOutBookings, dayLaneCounts }
}

const getCalendarGridStyle = (weekDays: Date[], dayLaneCounts: Record<string, number>, isMobile: boolean) => {
  if (isMobile) {
    const dayWidths = weekDays.map(day => {
      const laneCount = dayLaneCounts[dateKey(day)] || 1
      return Math.max(MOBILE_MIN_DAY_WIDTH, laneCount * MOBILE_MIN_LANE_WIDTH)
    })
    const minWidth = MOBILE_TIME_COLUMN_WIDTH + dayWidths.reduce((sum, width) => sum + width, 0)
    const dayHeight = ((DAY_END_MINUTES - DAY_START_MINUTES) / 60) * MOBILE_HOUR_HEIGHT
    return {
      minWidth: `${minWidth}px`,
      gridTemplateColumns: `${MOBILE_TIME_COLUMN_WIDTH}px ${dayWidths.map(width => `minmax(${width}px, ${width}px)`).join(' ')}`,
      gridTemplateRows: `38px minmax(${dayHeight}px, auto)`,
      '--calendar-hour-height': `${MOBILE_HOUR_HEIGHT}px`,
      '--calendar-day-height': `${dayHeight}px`,
    } as CSSProperties
  }

  const dayWidths = weekDays.map(day => {
    const laneCount = dayLaneCounts[dateKey(day)] || 1
    return Math.max(MIN_DAY_WIDTH, laneCount * MIN_LANE_WIDTH)
  })
  const minWidth = TIME_COLUMN_WIDTH + dayWidths.reduce((sum, width) => sum + width, 0)
  const dayHeight = ((DAY_END_MINUTES - DAY_START_MINUTES) / 60) * HOUR_HEIGHT

  return {
    minWidth: `${minWidth}px`,
    gridTemplateColumns: `${TIME_COLUMN_WIDTH}px ${dayWidths.map(width => `minmax(${width}px, ${width}px)`).join(' ')}`,
    gridTemplateRows: `44px minmax(${dayHeight}px, auto)`,
    '--calendar-hour-height': `${HOUR_HEIGHT}px`,
    '--calendar-day-height': `${dayHeight}px`,
  } as CSSProperties
}

const formatUnavailabilityDate = (value: string) => {
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', weekday: 'short' })
}

function AnimatorSchedulePage() {
  const { currentUser } = useAppLayoutContext()
  const isMobile = useIsMobile()
  const [activeView, setActiveView] = useState<'schedule' | 'availability'>('schedule')
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()))
  const [animators, setAnimators] = useState<AnimatorOption[]>([])
  const [animatorAvailability, setAnimatorAvailability] = useState<AnimatorAvailability[]>([])
  const [bookings, setBookings] = useState<AnimatorBooking[]>([])
  const [unavailability, setUnavailability] = useState<UnavailabilityItem[]>([])
  const [form, setForm] = useState<BookingFormState>(() => initialForm())
  const [unavailabilityForm, setUnavailabilityForm] = useState<UnavailabilityFormState>(() => initialUnavailabilityForm())
  const [selectedBookingId, setSelectedBookingId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [availabilityLoading, setAvailabilityLoading] = useState(false)
  const [availabilityRefreshKey, setAvailabilityRefreshKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [unavailabilitySaving, setUnavailabilitySaving] = useState(false)
  const [unavailabilityDeletingId, setUnavailabilityDeletingId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)), [weekStart])
  const weekStartKey = dateKey(weekStart)
  const weekEndKey = dateKey(addDays(weekStart, 6))

  const bookingLayoutResult = useMemo(() => getBookingLayout(bookings), [bookings])
  const bookingLayouts = bookingLayoutResult.bookings
  const calendarGridStyle = useMemo(
    () => getCalendarGridStyle(weekDays, bookingLayoutResult.dayLaneCounts, isMobile),
    [weekDays, bookingLayoutResult, isMobile],
  )
  const selectedBooking = useMemo(
    () => bookings.find(booking => booking.id === selectedBookingId) || null,
    [bookings, selectedBookingId],
  )
  const bookingByDay = useMemo(() => {
    return bookingLayouts.reduce<Record<string, BookingLayout[]>>((acc, booking) => {
      if (!acc[booking.event_date]) acc[booking.event_date] = []
      acc[booking.event_date].push(booking)
      return acc
    }, {})
  }, [bookingLayouts])

  const conflictCount = bookings.filter(booking => booking.has_conflict).length
  const rehearsalCount = bookings.filter(booking => booking.event_type === 'rehearsal').length
  const orderCount = bookings.length - rehearsalCount
  const maxConcurrentOrders = Math.max(0, ...Object.values(bookingLayoutResult.dayLaneCounts))
  const parallelCount = maxConcurrentOrders > 1 ? maxConcurrentOrders : 0
  const canManageSchedule = roleMatches(currentUser?.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])
  const canManageUnavailability = roleMatches(currentUser?.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN', 'MANAGER'])
  const canReportUnavailability = canManageUnavailability || roleMatches(currentUser?.role, ['USER'])
  const visibleAnimators = animatorAvailability.length
    ? animatorAvailability
    : animators.map(animator => ({
        ...animator,
        is_available: true,
        conflict_count: 0,
        conflicting_bookings: [],
        conflicting_unavailability: [],
      }))
  const selectedBusyAnimators = visibleAnimators.filter(
    animator => form.assigned_animator_ids.includes(animator.id) && !animator.is_available,
  )
  const unavailabilityAnimatorOptions = canManageUnavailability
    ? animators
    : animators.filter(animator => animator.id === currentUser?.id)
  const calendarHourHeight = isMobile ? MOBILE_HOUR_HEIGHT : HOUR_HEIGHT
  const minBookingHeight = isMobile ? 54 : 60
  const compactBookingHeight = isMobile ? 56 : 80
  const laneGapSize = isMobile ? 5 : 8

  const loadSchedule = async () => {
    const token = localStorage.getItem('crm_token')
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const headers = { Authorization: `Bearer ${token}` }
      const params = { ...getWorkspaceParams(currentUser), date_from: weekStartKey, date_to: weekEndKey }
      const [animatorsRes, bookingsRes, unavailabilityRes] = await Promise.all([
        axios.get('/animator-schedule/animators', { headers, params: getWorkspaceParams(currentUser) }),
        axios.get('/animator-schedule/bookings', { headers, params }),
        axios.get('/animator-schedule/unavailability', { headers, params }),
      ])
      setAnimators(Array.isArray(animatorsRes.data) ? animatorsRes.data : [])
      setBookings(Array.isArray(bookingsRes.data) ? bookingsRes.data : [])
      setUnavailability(Array.isArray(unavailabilityRes.data) ? unavailabilityRes.data : [])
      setAvailabilityRefreshKey(prev => prev + 1)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось загрузить график аниматоров')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSchedule()
  }, [weekStartKey, weekEndKey, currentUser?.workspace_id])

  useEffect(() => {
    if (!canManageSchedule) {
      setSelectedBookingId(null)
      setAnimatorAvailability([])
    }
  }, [canManageSchedule])

  useEffect(() => {
    setUnavailabilityForm(prev => {
      if (prev.animator_id && (canManageUnavailability || prev.animator_id === currentUser?.id)) return prev
      const fallbackAnimatorId = canManageUnavailability
        ? animators[0]?.id
        : currentUser?.id
      if (!fallbackAnimatorId || prev.animator_id === fallbackAnimatorId) return prev
      return { ...prev, animator_id: fallbackAnimatorId }
    })
  }, [animators, canManageUnavailability, currentUser?.id])

  useEffect(() => {
    const token = localStorage.getItem('crm_token')
    const duration = Number(form.duration_minutes)
    if (!token || !canManageSchedule || !form.event_date || !form.start_time || !duration || duration < 15) {
      setAnimatorAvailability([])
      return
    }

    let cancelled = false
    const loadAvailability = async () => {
      setAvailabilityLoading(true)
      try {
        const response = await axios.get('/animator-schedule/animators/availability', {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            ...getWorkspaceParams(currentUser),
            event_date: form.event_date,
            start_time: form.start_time,
            duration_minutes: duration,
            exclude_booking_id: selectedBookingId || undefined,
          },
        })
        if (!cancelled) {
          setAnimatorAvailability(Array.isArray(response.data) ? response.data : [])
        }
      } catch {
        if (!cancelled) {
          setAnimatorAvailability([])
        }
      } finally {
        if (!cancelled) {
          setAvailabilityLoading(false)
        }
      }
    }

    void loadAvailability()
    return () => {
      cancelled = true
    }
  }, [
    availabilityRefreshKey,
    canManageSchedule,
    currentUser?.workspace_id,
    form.event_date,
    form.start_time,
    form.duration_minutes,
    selectedBookingId,
  ])

  const updateForm = (key: keyof BookingFormState, value: string | string[]) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const updateUnavailabilityForm = (key: keyof UnavailabilityFormState, value: string) => {
    setUnavailabilityForm(prev => ({ ...prev, [key]: value }))
  }

  const toggleAnimator = (animatorId: string) => {
    setForm(prev => {
      const isSelected = prev.assigned_animator_ids.includes(animatorId)
      return {
        ...prev,
        assigned_animator_ids: isSelected
          ? prev.assigned_animator_ids.filter(id => id !== animatorId)
          : [...prev.assigned_animator_ids, animatorId],
      }
    })
  }

  const showBooking = (booking: AnimatorBooking) => {
    if (!canManageSchedule) return
    setSelectedBookingId(booking.id)
    setForm(formFromBooking(booking))
    setError('')
  }

  const resetForm = () => {
    setSelectedBookingId(null)
    setForm(initialForm(form.event_date || weekStartKey))
    setError('')
  }

  const refreshAfterSave = async (eventDate: string) => {
    const targetWeekStart = startOfWeek(new Date(`${eventDate}T00:00:00`))
    if (dateKey(targetWeekStart) !== weekStartKey) {
      setWeekStart(targetWeekStart)
      return
    }
    await loadSchedule()
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const token = localStorage.getItem('crm_token')
    if (!token || !canManageSchedule) return
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...form,
        duration_minutes: Number(form.duration_minutes || 60),
        price: form.price ? Number(form.price) : null,
        prepayment: form.prepayment ? Number(form.prepayment) : null,
      }
      const request = selectedBookingId
        ? axios.patch(`/animator-schedule/bookings/${selectedBookingId}`, payload, {
            headers: { Authorization: `Bearer ${token}` },
            params: getWorkspaceParams(currentUser),
          })
        : axios.post('/animator-schedule/bookings', payload, {
            headers: { Authorization: `Bearer ${token}` },
            params: getWorkspaceParams(currentUser),
          })
      const response = await request
      if (selectedBookingId && response.data?.id) {
        setSelectedBookingId(response.data.id)
        setForm(formFromBooking(response.data))
      } else {
        setForm(initialForm(form.event_date))
      }
      await refreshAfterSave(form.event_date)
    } catch (err: any) {
      const actionLabel = getEventTypeActionLabel(form.event_type)
      setError(err?.response?.data?.detail || (selectedBookingId ? `Не удалось обновить ${actionLabel}` : `Не удалось создать ${actionLabel}`))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedBookingId) return
    const token = localStorage.getItem('crm_token')
    if (!token || !canManageSchedule) return
    if (!window.confirm(`Удалить ${getEventTypeActionLabel(form.event_type)} из графика?`)) return
    setDeleting(true)
    setError('')
    try {
      await axios.delete(`/animator-schedule/bookings/${selectedBookingId}`, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams(currentUser),
      })
      const lastDate = form.event_date || weekStartKey
      setSelectedBookingId(null)
      setForm(initialForm(lastDate))
      await loadSchedule()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось удалить событие')
    } finally {
      setDeleting(false)
    }
  }

  const handleUnavailabilitySubmit = async (event: FormEvent) => {
    event.preventDefault()
    const token = localStorage.getItem('crm_token')
    if (!token || !canReportUnavailability || !unavailabilityForm.animator_id) return
    setUnavailabilitySaving(true)
    setError('')
    try {
      await axios.post('/animator-schedule/unavailability', {
        ...unavailabilityForm,
        duration_minutes: Number(unavailabilityForm.duration_minutes || 60),
      }, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams(currentUser),
      })
      const lastDate = unavailabilityForm.unavailable_date || weekStartKey
      const lastAnimatorId = unavailabilityForm.animator_id
      setUnavailabilityForm(initialUnavailabilityForm(lastDate, lastAnimatorId))
      await loadSchedule()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось добавить занятость')
    } finally {
      setUnavailabilitySaving(false)
    }
  }

  const handleUnavailabilityDelete = async (item: UnavailabilityItem) => {
    const token = localStorage.getItem('crm_token')
    if (!token || !canReportUnavailability) return
    if (!canManageUnavailability && item.animator_id !== currentUser?.id) return
    if (!window.confirm('Удалить эту занятость?')) return
    setUnavailabilityDeletingId(item.id)
    setError('')
    try {
      await axios.delete(`/animator-schedule/unavailability/${item.id}`, {
        headers: { Authorization: `Bearer ${token}` },
        params: getWorkspaceParams(currentUser),
      })
      await loadSchedule()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Не удалось удалить занятость')
    } finally {
      setUnavailabilityDeletingId(null)
    }
  }

  const hourLabels = Array.from({ length: (DAY_END_MINUTES - DAY_START_MINUTES) / 60 + 1 }, (_, index) => {
    const hour = 8 + index
    const period = hour < 12 ? 'AM' : 'PM'
    const displayHour = hour % 12 || 12
    return `${displayHour}:00 ${period}`
  })

  return (
    <div className="animator-schedule-page">
      <header className="animator-schedule-head">
        <div>
          <h1>График</h1>
          <p>Заказы и репетиции по времени, длительности и назначенным исполнителям.</p>
        </div>
        <div className="animator-schedule-stats">
          <span>{bookings.length} событий</span>
          <span>{orderCount} заказов</span>
          <span>{rehearsalCount} репетиций</span>
          <span>{parallelCount} параллельно</span>
          <span className={conflictCount ? 'is-danger' : ''}>{conflictCount} накладок</span>
        </div>
      </header>

      <section className="animator-schedule-controls" aria-label="Schedule controls">
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => setWeekStart(addDays(weekStart, -7))}>
          Назад
        </button>
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => setWeekStart(startOfWeek(new Date()))}>
          Сегодня
        </button>
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => setWeekStart(addDays(weekStart, 7))}>
          Вперед
        </button>
        <input
          type="date"
          value={weekStartKey}
          onChange={event => setWeekStart(startOfWeek(new Date(`${event.target.value}T00:00:00`)))}
          aria-label="Выбрать неделю"
        />
      </section>

      <div className="animator-view-tabs" role="tablist" aria-label="Раздел графика аниматоров">
        <button
          type="button"
          className={activeView === 'schedule' ? 'is-active' : ''}
          onClick={() => setActiveView('schedule')}
        >
          График
        </button>
        <button
          type="button"
          className={activeView === 'availability' ? 'is-active' : ''}
          onClick={() => setActiveView('availability')}
        >
          Занятость
        </button>
      </div>

      {error && <div className="animator-schedule-error">{error}</div>}

      {activeView === 'schedule' ? (
      <div className="animator-schedule-workspace">
        <section className="animator-calendar animator-calendar--timeline" aria-label="Animator weekly schedule">
          <div className="animator-calendar-grid" style={calendarGridStyle}>
            <div className="animator-calendar-corner" />
            {weekDays.map(day => (
              <div key={dateKey(day)} className="animator-calendar-day-head">
                <span>{day.toLocaleDateString('ru-RU', { weekday: 'short' })}</span>
                <strong>{day.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })}</strong>
              </div>
            ))}

            <div className="animator-calendar-times">
              {hourLabels.map(label => (
                <div key={label}>{label}</div>
              ))}
            </div>

            {weekDays.map(day => {
              const dayKey = dateKey(day)
              const dayBookings = bookingByDay[dayKey] || []
              return (
                <div key={dayKey} className="animator-calendar-day">
                  {hourLabels.slice(0, -1).map(label => (
                    <div key={label} className="animator-hour-line" />
                  ))}
                  {dayBookings.map(booking => {
                    const top = Math.max(0, (booking.starts_at_minutes - DAY_START_MINUTES) * (calendarHourHeight / 60))
                    const height = Math.max(minBookingHeight, (booking.ends_at_minutes - booking.starts_at_minutes) * (calendarHourHeight / 60) - 4)
                    const laneWidth = 100 / booking.laneCount
                    const laneGap = booking.laneCount > 1 ? laneGapSize : 0
                    const style = {
                      '--booking-top': `${top}px`,
                      '--booking-height': `${height}px`,
                      '--booking-left': `calc(${booking.laneIndex * laneWidth}% + ${laneGap / 2}px)`,
                      '--booking-width': `calc(${laneWidth}% - ${laneGap}px)`,
                      '--booking-color': booking.color,
                    } as CSSProperties

                    return (
                      <button
                        type="button"
                        key={booking.id}
                        className={[
                          'animator-booking',
                          booking.event_type === 'rehearsal' ? 'is-rehearsal' : '',
                          booking.has_conflict ? 'is-conflict' : '',
                          selectedBookingId === booking.id ? 'is-selected' : '',
                          height < compactBookingHeight ? 'is-compact' : '',
                          canManageSchedule ? '' : 'is-readonly',
                        ].filter(Boolean).join(' ')}
                        style={style}
                        onClick={() => showBooking(booking)}
                        disabled={!canManageSchedule}
                        aria-label={canManageSchedule ? `Редактировать ${getEventTypeActionLabel(booking.event_type)} ${booking.title}` : `${getEventTypeLabel(booking.event_type)} ${booking.title}`}
                      >
                        <div className="animator-booking-time">{booking.start_time} - {booking.end_time}</div>
                        <span className="animator-booking-type">{getEventTypeLabel(booking.event_type)}</span>
                        <h3>{booking.title}</h3>
                        <p>{booking.program_name || 'Программа'} · {booking.client_name}</p>
                        <p>{booking.assigned_animators.map(animator => animator.full_name).join(', ') || 'Аниматор не назначен'}</p>
                        {booking.has_conflict && <strong>Накладка по аниматору</strong>}
                      </button>
                    )
                  })}
                </div>
              )
            })}
          </div>
          {loading && <div className="animator-loading">Загрузка графика...</div>}
        </section>

        <aside className="animator-order-panel">
          {canManageSchedule ? (
            <>
              <div className="animator-order-panel-head">
                <h2>{selectedBooking ? `Редактирование: ${getEventTypeLabel(form.event_type).toLowerCase()}` : `Новое событие`}</h2>
                {selectedBooking && (
                  <button type="button" className="btn btn--secondary btn--sm" onClick={resetForm}>
                    Новый
                  </button>
                )}
              </div>
              {selectedBooking && (
                <p className="animator-edit-note">
                  Выбрано событие {selectedBooking.start_time} - {selectedBooking.end_time}. После сохранения график пересчитает накладки.
                </p>
              )}
              <form onSubmit={handleSubmit} className="animator-order-form">
            <label>
              Тип события
              <select value={form.event_type} onChange={event => updateForm('event_type', event.target.value as BookingEventType)}>
                <option value="order">Заказ</option>
                <option value="rehearsal">Репетиция</option>
              </select>
            </label>
            <label>
              {form.event_type === 'rehearsal' ? 'Название репетиции' : 'Название заказа'}
              <input value={form.title} onChange={event => updateForm('title', event.target.value)} required placeholder={form.event_type === 'rehearsal' ? 'Репетиция нового шоу' : 'День рождения Софии'} />
            </label>
            <label>
              {form.event_type === 'rehearsal' ? 'Организатор / группа' : 'Клиент'}
              <input value={form.client_name} onChange={event => updateForm('client_name', event.target.value)} required placeholder={form.event_type === 'rehearsal' ? 'Prime Event' : 'Имя клиента'} />
            </label>
            <label>
              Телефон
              <input value={form.client_phone} onChange={event => updateForm('client_phone', event.target.value)} placeholder="+998..." />
            </label>
            <div className="animator-form-row">
              <label>
                Дата
                <input type="date" value={form.event_date} onChange={event => updateForm('event_date', event.target.value)} required />
              </label>
              <label>
                Начало
                <input type="time" value={form.start_time} onChange={event => updateForm('start_time', event.target.value)} required />
              </label>
            </div>
            <div className="animator-form-row">
              <label>
                Длительность
                <input type="number" min="15" step="15" value={form.duration_minutes} onChange={event => updateForm('duration_minutes', event.target.value)} required />
              </label>
              <label>
                Стоимость
                <input type="number" min="0" value={form.price} onChange={event => updateForm('price', event.target.value)} placeholder="0" />
              </label>
            </div>
            <div className="animator-form-row">
              <label>
                Предоплата
                <input type="number" min="0" value={form.prepayment} onChange={event => updateForm('prepayment', event.target.value)} placeholder="0" />
              </label>
              <label>
                Статус оплаты
                <select value={form.payment_status} onChange={event => updateForm('payment_status', event.target.value)}>
                  <option value="pending">Ожидает оплаты</option>
                  <option value="prepaid">Предоплата</option>
                  <option value="paid">Оплачено</option>
                  <option value="refunded">Возврат</option>
                </select>
              </label>
            </div>
            <label>
              Программа
              <input value={form.program_name} onChange={event => updateForm('program_name', event.target.value)} placeholder="Человек-паук, шоу мыльных пузырей" />
            </label>
            <label>
              Адрес
              <input value={form.address} onChange={event => updateForm('address', event.target.value)} placeholder="Локация мероприятия" />
            </label>
            <div className="animator-assignment-field">
              <span className="animator-field-label">Аниматоры</span>
              <div className="animator-assignment-list" role="group" aria-label="Назначение аниматоров">
                {visibleAnimators.map(animator => {
                  const isSelected = form.assigned_animator_ids.includes(animator.id)
                  return (
                    <button
                      key={animator.id}
                      type="button"
                      className={[
                        'animator-assignment-option',
                        isSelected ? 'is-selected' : '',
                        animator.is_available ? 'is-available' : 'is-busy',
                      ].filter(Boolean).join(' ')}
                      onClick={() => toggleAnimator(animator.id)}
                      aria-pressed={isSelected}
                    >
                      <span className="animator-assignment-main">
                        <span className="animator-assignment-check">{isSelected ? '✓' : ''}</span>
                        <span>
                          <strong>{animator.full_name}</strong>
                        </span>
                      </span>
                      <span className="animator-assignment-status">
                        {animator.is_available ? 'Свободен' : 'Занят'}
                      </span>
                        {animator.conflicting_bookings.map(conflict => (
                          <span key={conflict.id} className="animator-assignment-conflict">
                            {conflict.start_time} - {conflict.end_time} · {getEventTypeLabel(conflict.event_type)}: {conflict.title}
                          </span>
                      ))}
                      {(animator.conflicting_unavailability || []).map(conflict => (
                        <span key={conflict.id} className="animator-assignment-conflict">
                          {conflict.start_time} - {conflict.end_time} · {conflict.reason}
                        </span>
                      ))}
                    </button>
                  )
                })}
                {visibleAnimators.length === 0 && (
                  <span className="animator-assignment-empty">Пока нет активных аниматоров в рабочем пространстве.</span>
                )}
              </div>
              {availabilityLoading && <span className="animator-assignment-hint">Проверяем занятость...</span>}
              {selectedBusyAnimators.length > 0 && (
                <span className="animator-assignment-warning">
                  Назначены занятые аниматоры: {selectedBusyAnimators.map(animator => animator.full_name).join(', ')}. Заказ сохранится, но в графике будет накладка.
                </span>
              )}
            </div>
            <label>
              Инвентарь и костюмы
              <textarea value={form.inventory_notes} onChange={event => updateForm('inventory_notes', event.target.value)} rows={3} placeholder="Костюмы, реквизит, техника" />
            </label>
            <label>
              Заметки
              <textarea value={form.notes} onChange={event => updateForm('notes', event.target.value)} rows={3} placeholder="Комментарий для координатора" />
            </label>
            <div className="animator-form-actions">
              <button type="submit" className="btn btn--primary" disabled={saving || deleting}>
                {saving ? 'Сохраняем...' : selectedBooking ? 'Сохранить изменения' : form.event_type === 'rehearsal' ? 'Добавить репетицию' : 'Создать заказ'}
              </button>
              {selectedBooking && (
                <button type="button" className="btn btn--secondary animator-delete-button" disabled={saving || deleting} onClick={handleDelete}>
                  {deleting ? 'Удаляем...' : 'Удалить'}
                </button>
              )}
            </div>
              </form>
            </>
          ) : (
            <div className="animator-readonly-panel">
              <h2>Просмотр графика</h2>
              <p>Добавлять, редактировать и удалять заказы и репетиции может только руководство с ролью администратора.</p>
              <div>
                <span>{bookings.length}</span>
                <small>событий на выбранной неделе</small>
              </div>
              <div>
                <span>{conflictCount}</span>
                <small>накладок требуют внимания</small>
              </div>
            </div>
          )}
        </aside>
      </div>
      ) : (
      <div className="animator-availability-workspace">
        <section className="animator-unavailability-panel" aria-label="Занятость аниматоров">
          <div className="animator-unavailability-head">
            <div>
              <h2>Занятость</h2>
              <p>Личные занятости аниматоров, которые учитываются при назначении заказов.</p>
            </div>
            <span>{unavailability.length} записей</span>
          </div>
          <div className="animator-unavailability-list">
            {unavailability.map(item => (
              <article key={item.id} className="animator-unavailability-item">
                <div>
                  <strong>{item.animator?.full_name || 'Аниматор'}</strong>
                  <span>{formatUnavailabilityDate(item.unavailable_date)} · {item.start_time} - {item.end_time}</span>
                </div>
                <p>{item.reason}</p>
                {item.notes && <small>{item.notes}</small>}
                {(canManageUnavailability || item.animator_id === currentUser?.id) && (
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm animator-delete-button"
                    disabled={unavailabilityDeletingId === item.id}
                    onClick={() => handleUnavailabilityDelete(item)}
                  >
                    {unavailabilityDeletingId === item.id ? 'Удаляем...' : 'Удалить'}
                  </button>
                )}
              </article>
            ))}
            {unavailability.length === 0 && (
              <div className="animator-unavailability-empty">На выбранной неделе занятость не добавлена.</div>
            )}
          </div>
          {loading && <div className="animator-loading">Загрузка занятости...</div>}
        </section>

        <aside className="animator-order-panel">
          {canReportUnavailability ? (
            <>
              <div className="animator-order-panel-head">
                <h2>Добавить занятость</h2>
              </div>
              <form onSubmit={handleUnavailabilitySubmit} className="animator-order-form">
                <label>
                  Аниматор
                  {canManageUnavailability ? (
                    <select
                      value={unavailabilityForm.animator_id}
                      onChange={event => updateUnavailabilityForm('animator_id', event.target.value)}
                      required
                    >
                      {unavailabilityAnimatorOptions.map(animator => (
                        <option key={animator.id} value={animator.id}>{animator.full_name}</option>
                      ))}
                    </select>
                  ) : (
                    <input value={currentUser?.full_name || 'Моя занятость'} disabled />
                  )}
                </label>
                <div className="animator-form-row">
                  <label>
                    Дата
                    <input
                      type="date"
                      value={unavailabilityForm.unavailable_date}
                      onChange={event => updateUnavailabilityForm('unavailable_date', event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Начало
                    <input
                      type="time"
                      value={unavailabilityForm.start_time}
                      onChange={event => updateUnavailabilityForm('start_time', event.target.value)}
                      required
                    />
                  </label>
                </div>
                <label>
                  Длительность
                  <input
                    type="number"
                    min="15"
                    step="15"
                    value={unavailabilityForm.duration_minutes}
                    onChange={event => updateUnavailabilityForm('duration_minutes', event.target.value)}
                    required
                  />
                </label>
                <label>
                  Причина
                  <input
                    value={unavailabilityForm.reason}
                    onChange={event => updateUnavailabilityForm('reason', event.target.value)}
                    placeholder="Личные дела, учеба, другой проект"
                    required
                  />
                </label>
                <label>
                  Заметки
                  <textarea
                    value={unavailabilityForm.notes}
                    onChange={event => updateUnavailabilityForm('notes', event.target.value)}
                    rows={3}
                    placeholder="Комментарий для менеджера"
                  />
                </label>
                <button type="submit" className="btn btn--primary" disabled={unavailabilitySaving || !unavailabilityForm.animator_id}>
                  {unavailabilitySaving ? 'Добавляем...' : 'Добавить занятость'}
                </button>
              </form>
            </>
          ) : (
            <div className="animator-readonly-panel">
              <h2>Просмотр занятости</h2>
              <p>Добавлять личную занятость могут аниматоры, а выставлять занятость другим аниматорам могут менеджеры.</p>
            </div>
          )}
        </aside>
      </div>
      )}
    </div>
  )
}

export default AnimatorSchedulePage
