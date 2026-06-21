import { useNavigate } from 'react-router-dom'
import { useI18n } from '../../shared/i18nContext'

function CrmModulesPage() {
  const navigate = useNavigate()
  const { t } = useI18n()

  return (
    <div className="crm-page-shell crm-section-page">
      <div className="page-head">
        <div className="page-head-left">
          <span className="page-greeting">{t('market.crmModules')}</span>
          <h1 className="page-h1">{t('modules.managedTitle')}</h1>
          <span className="page-sub">{t('modules.managedDescription')}</span>
        </div>
      </div>

      <section className="section crm-section-panel">
        <div className="section-head">
          <h2 className="section-title">{t('nav.superadmin')}</h2>
          <span className="section-sub">{t('home.enabledShell')}</span>
        </div>
        <div className="page-head-actions">
          <button type="button" className="btn btn--primary" onClick={() => navigate('/superadmin')}>
            {t('modules.openSuperadmin')}
          </button>
          <button type="button" className="btn btn--secondary" onClick={() => navigate('/home')}>
            {t('nav.home')}
          </button>
        </div>
      </section>
    </div>
  )
}

export default CrmModulesPage
