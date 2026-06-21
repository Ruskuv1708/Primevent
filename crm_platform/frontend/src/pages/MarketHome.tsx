import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { getWorkspaceParams } from '../shared/workspace'
import { getMarketShell, type MarketWidget } from '../shared/marketShell'
import { isModuleEnabled } from '../shared/modules'
import type { RequestItem } from '../features/requests/types'
import { useAppLayoutContext } from '../shared/appLayoutContext'
import { useI18n } from '../shared/i18nContext'
import type { TranslationKey } from '../shared/i18n'

type HomeAnimator = {
  id: string
  full_name: string
  email?: string
}

type HomeScheduleBooking = {
  id: string
  event_type?: 'order' | 'rehearsal'
  title: string
  client_name: string
  event_date: string
  start_time: string
  end_time: string
  program_name?: string
  assigned_animators: HomeAnimator[]
  has_conflict: boolean
}

type TFunction = (key: TranslationKey) => string

const presetLabelKey: Record<string, TranslationKey> = {
  functional: 'market.functional',
}

const widgetLabelKey: Record<string, TranslationKey> = {
  attention: 'market.needsAttention',
  'recent-work': 'market.recentWork',
  'schedule-conflicts': 'market.scheduleConflicts',
}

const getWidgetValue = (
  widget: MarketWidget,
  requests: RequestItem[],
  requestsLoading: boolean,
  scheduleBookings: HomeScheduleBooking[],
  scheduleLoading: boolean,
  t: TFunction,
) => {
  if (widget.source === 'requests') {
    if (requestsLoading) return '...'
    if (widget.id === 'new-leads') {
      return requests.filter(request => request.status === 'new').length
    }
    if (widget.id === 'pending-tasks' || widget.id === 'pending-requests') {
      return requests.filter(request => request.status === 'pending').length
    }
    if (widget.id === 'follow-ups' || widget.id === 'exceptions') {
      return requests.filter(request => request.status !== 'done').length
    }
    return requests.length
  }
  if (widget.source === 'schedule') {
    if (scheduleLoading) return '...'
    if (widget.id === 'schedule-conflicts') {
      return scheduleBookings.filter(booking => booking.has_conflict).length
    }
    return scheduleBookings.length
  }
  return t('home.soon')
}

const getWidgetHelper = (widget: MarketWidget, t: TFunction) => {
  if (widget.source === 'requests') return t('home.liveWorkflowData')
  if (widget.source === 'templates') return t('home.installedTemplates')
  if (widget.source === 'schedule') return t('home.weekEventsSub')
  return t('home.readyForSetup')
}

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

const getEventTypeLabel = (eventType: HomeScheduleBooking['event_type']) => (
  eventType === 'rehearsal' ? 'Репетиция' : 'Заказ'
)

function MarketHome() {
  const { currentUser, enabledModules } = useAppLayoutContext()
  const { t } = useI18n()
  const [requests, setRequests] = useState<RequestItem[]>([])
  const [requestsLoading, setRequestsLoading] = useState(true)
  const [scheduleBookings, setScheduleBookings] = useState<HomeScheduleBooking[]>([])
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const weekStart = useMemo(() => startOfWeek(new Date()), [])
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)), [weekStart])
  const weekStartKey = dateKey(weekStart)
  const weekEndKey = dateKey(addDays(weekStart, 6))
  const navigate = useNavigate()
  const shell = useMemo(() => getMarketShell(), [])
  const scheduleEnabled = isModuleEnabled(enabledModules, 'animator_schedule')
  const visibleWidgets = useMemo(() => {
    return shell.widgets.filter(widget => {
      if (widget.source === 'requests') return isModuleEnabled(enabledModules, 'workflow')
      if (widget.source === 'templates') return isModuleEnabled(enabledModules, 'dynamic_forms')
      if (widget.source === 'schedule') return isModuleEnabled(enabledModules, 'animator_schedule')
      return true
    })
  }, [enabledModules, shell.widgets])
  const shellLabel = t(presetLabelKey[shell.modulePreset] || 'market.functional')

  useEffect(() => {
    let isActive = true

    ;(async () => {
      const token = localStorage.getItem('crm_token')
      if (!token) {
        navigate('/')
        return
      }
      if (!isModuleEnabled(enabledModules, 'workflow')) {
        setRequests([])
        setRequestsLoading(false)
        return
      }

      setRequestsLoading(true)
      try {
        const requestRes = await axios.get<RequestItem[]>('/workflow/requests', {
          headers: { Authorization: `Bearer ${token}` },
          params: getWorkspaceParams(currentUser),
        }).catch(() => ({ data: [] as RequestItem[] }))
        if (!isActive) return
        setRequests(Array.isArray(requestRes.data) ? requestRes.data : [])
      } catch (err) {
        console.error('Failed to load market home:', err)
      } finally {
        if (isActive) setRequestsLoading(false)
      }
    })()
    return () => {
      isActive = false
    }
  }, [currentUser?.id, currentUser?.role, currentUser?.workspace_id, enabledModules, navigate])

  useEffect(() => {
    let isActive = true

    ;(async () => {
      const token = localStorage.getItem('crm_token')
      if (!token || !scheduleEnabled) {
        setScheduleBookings([])
        setScheduleLoading(false)
        return
      }

      setScheduleLoading(true)
      try {
        const response = await axios.get<HomeScheduleBooking[]>('/animator-schedule/bookings', {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            ...getWorkspaceParams(currentUser),
            date_from: weekStartKey,
            date_to: weekEndKey,
          },
        })
        if (!isActive) return
        setScheduleBookings(Array.isArray(response.data) ? response.data : [])
      } catch (err) {
        console.error('Failed to load home schedule events:', err)
        if (isActive) setScheduleBookings([])
      } finally {
        if (isActive) setScheduleLoading(false)
      }
    })()

    return () => {
      isActive = false
    }
  }, [currentUser?.workspace_id, enabledModules, scheduleEnabled, weekStartKey, weekEndKey])

  return (
    <div className="crm-page-shell crm-home">
      <div className="page-head">
        <div className="page-head-left">
          <span className="page-greeting">{shellLabel}</span>
          <h1 className="page-h1">{t('home.welcomeBack')}{currentUser?.full_name ? `, ${currentUser.full_name}` : ''}</h1>
          <span className="page-sub">{t('home.subtitle')}</span>
        </div>
      </div>

      {visibleWidgets.length > 0 && (
        <div
          className="metrics"
          style={{ '--metric-cols': Math.max(visibleWidgets.length, 1) } as CSSProperties}
        >
          {visibleWidgets.map(widget => (
            <button
              key={widget.id}
              type="button"
              className="metric"
              onClick={() => navigate(widget.source === 'templates' ? '/forms' : widget.source === 'schedule' ? '/animator-schedule' : '/work')}
            >
              <span className="metric-label">{t(widgetLabelKey[widget.id] || 'market.needsAttention')}</span>
              <span className="metric-value">{getWidgetValue(widget, requests, requestsLoading, scheduleBookings, scheduleLoading, t)}</span>
              <span className={widget.tone === 'attention' ? 'metric-delta delta--down' : widget.tone === 'success' ? 'metric-delta delta--up' : 'metric-delta delta--flat'}>
                {getWidgetHelper(widget, t)}
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="crm-home-grid">
        {scheduleEnabled && (
          <section className="section crm-section-panel home-events-panel">
            <div className="section-head">
              <div>
                <h2 className="section-title">{t('home.weekEvents')}</h2>
                <span className="section-sub">{t('home.weekEventsSub')}</span>
              </div>
              <button type="button" className="btn btn--secondary btn--sm" onClick={() => navigate('/animator-schedule')}>
                {t('home.openSchedule')}
              </button>
            </div>
            <div className="animator-mobile-agenda-list">
              {weekDays.map(day => {
                const dayKey = dateKey(day)
                const dayBookings = scheduleBookings.filter(booking => booking.event_date === dayKey)
                return (
                  <div key={dayKey} className="animator-mobile-agenda-day">
                    <div className="animator-mobile-agenda-date">
                      <span>{day.toLocaleDateString('ru-RU', { weekday: 'short' })}</span>
                      <strong>{day.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })}</strong>
                    </div>
                    <div className="animator-mobile-agenda-events">
                      {scheduleLoading ? (
                        <span className="animator-mobile-agenda-empty">{t('common.loading')}</span>
                      ) : dayBookings.length === 0 ? (
                        <span className="animator-mobile-agenda-empty">{t('home.noEvents')}</span>
                      ) : dayBookings.map(booking => (
                        <button
                          type="button"
                          key={booking.id}
                          className={booking.has_conflict ? 'animator-mobile-event is-conflict' : 'animator-mobile-event'}
                          onClick={() => navigate('/animator-schedule')}
                        >
                          <span>{booking.start_time} - {booking.end_time} · {getEventTypeLabel(booking.event_type)}</span>
                          <strong>{booking.title}</strong>
                          <small>{booking.assigned_animators.map(animator => animator.full_name).join(', ') || t('home.noAnimator')}</small>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

export default MarketHome
