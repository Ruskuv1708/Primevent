import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMarketShell, type MarketSectionId } from '../shared/marketShell'
import { roleMatches } from '../shared/roleLabels'
import { isModuleEnabled } from '../shared/modules'
import { useAppLayoutContext } from '../shared/appLayoutContext'
import { useI18n } from '../shared/i18nContext'
import type { TranslationKey } from '../shared/i18n'

type MarketSectionPageProps = {
  sectionId: Exclude<MarketSectionId, 'home'>
}

const SECTION_COPY_KEYS: Record<Exclude<MarketSectionId, 'home'>, TranslationKey> = {
  people: 'market.peopleDescription',
  work: 'market.workDescription',
  money: 'market.moneyDescription',
  reports: 'market.reportsDescription',
  settings: 'market.settingsDescription',
}

const SECTION_LABEL_KEYS: Record<MarketSectionId, TranslationKey> = {
  home: 'nav.home',
  people: 'nav.people',
  work: 'nav.work',
  money: 'nav.money',
  reports: 'nav.reports',
  settings: 'nav.settings',
}

const PRESET_LABEL_KEYS: Record<string, TranslationKey> = {
  functional: 'market.functional',
}

function MarketSectionPage({ sectionId }: MarketSectionPageProps) {
  const { currentUser, enabledModules } = useAppLayoutContext()
  const { t } = useI18n()
  const navigate = useNavigate()
  const shell = useMemo(() => getMarketShell(), [])
  const sectionLinks = useMemo(() => {
    const isAdmin = roleMatches(currentUser?.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])
    const isManager = roleMatches(currentUser?.role, ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN', 'MANAGER'])

    if (sectionId === 'people') {
      return isModuleEnabled(enabledModules, 'registry')
        ? [{ label: t('market.openRecords'), to: '/registry' }]
        : []
    }
    if (sectionId === 'work') {
      return [
        ...(isModuleEnabled(enabledModules, 'open_requests') ? [{ label: t('market.openRequests'), to: '/requests' }] : []),
        ...(isModuleEnabled(enabledModules, 'assigned_work') ? [{ label: t('market.openAssignedWork'), to: '/requests/assigned' }] : []),
        ...(isModuleEnabled(enabledModules, 'departments') && isManager ? [{ label: t('market.departments'), to: '/departments' }] : []),
      ]
    }
    if (sectionId === 'money') {
      return isModuleEnabled(enabledModules, 'form_templates')
        ? [{ label: t('market.openForms'), to: '/forms' }]
        : []
    }
    if (sectionId === 'reports') {
      return isModuleEnabled(enabledModules, 'report_library')
        ? [
            { label: t('market.openReports'), to: '/reports' },
            ...(isModuleEnabled(enabledModules, 'report_types') && isAdmin ? [{ label: t('market.reportTypes'), to: '/report-types' }] : []),
          ]
        : []
    }
    return [
      ...(isModuleEnabled(enabledModules, 'profile') ? [{ label: t('market.openProfile'), to: '/profile' }] : []),
      ...(isModuleEnabled(enabledModules, 'ai_architect') ? [{ label: t('market.openAiArchitect'), to: '/ai-architect' }] : []),
      ...(isModuleEnabled(enabledModules, 'admin_panel') && isAdmin ? [{ label: t('market.adminPanel'), to: '/admin' }] : []),
      ...(isModuleEnabled(enabledModules, 'superadmin_panel') && roleMatches(currentUser?.role, ['SUPERADMIN'])
        ? [{ label: t('nav.superadmin'), to: '/superadmin' }]
        : []),
    ]
  }, [currentUser?.role, enabledModules, sectionId, t])

  return (
    <div className="crm-page-shell crm-section-page">
      <div className="page-head">
        <div className="page-head-left">
          <span className="page-greeting">{t(PRESET_LABEL_KEYS[shell.modulePreset] || 'market.functional')}</span>
          <h1 className="page-h1">{t(SECTION_LABEL_KEYS[sectionId])}</h1>
          <span className="page-sub">{t(SECTION_COPY_KEYS[sectionId])}</span>
        </div>
      </div>

      <section className="section crm-section-panel">
        <div className="section-head">
          <h2 className="section-title">{t('market.availableNow')}</h2>
          <span className="section-sub">{sectionLinks.length} {t('market.destinations')}</span>
        </div>
        <div className="crm-action-list">
          {sectionLinks.map(link => (
            <button
              key={link.to}
              type="button"
              className="crm-action-item"
              onClick={() => navigate(link.to)}
            >
              <span>{link.label}</span>
              <svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                <path d="M7 4l6 6-6 6" />
              </svg>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}

export default MarketSectionPage
