import { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import { resetUiModeSelectionForSession } from '../shared/uiMode'
import { useI18n } from '../shared/i18nContext'
import { LANGUAGE_OPTIONS, normalizeLanguage } from '../shared/language'

function Login() {
  const { language, setLanguage, t } = useI18n()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSubmitting(true)

    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    try {
      const response = await axios.post('/access/token', formData)
      const token = response.data.access_token
      localStorage.setItem('crm_token', token)
      setLanguage(normalizeLanguage(response.data?.user?.language))
      resetUiModeSelectionForSession()
      navigate('/home')
    } catch (err) {
      console.error(err)
      setError(t('login.invalidCredentials'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="crm-login-screen">
      <section className="crm-login-hero">
        <div className="crm-login-brand">
          <span className="crm-login-mark">P</span>
          <span>Prime Event CRM</span>
        </div>

        <div className="crm-login-copy">
          <h1>{t('login.heroTitle')}</h1>
          <p>{t('login.heroCopy')}</p>
        </div>

        <div className="crm-login-metrics" aria-label="CRM workspace metrics">
          <div className="crm-login-metric">
            <strong>48px</strong>
            <span>toolbar</span>
          </div>
          <div className="crm-login-metric">
            <strong>40px</strong>
            <span>rows</span>
          </div>
          <div className="crm-login-metric">
            <strong>13px</strong>
            <span>base type</span>
          </div>
        </div>
      </section>

      <section className="crm-login-panel" aria-label="Sign in">
        <form className="crm-login-form" onSubmit={handleLogin}>
          <div>
            <h2>{t('login.signIn')}</h2>
            <p>{t('login.useAccount')}</p>
          </div>

          <div className="crm-language-switch" role="group" aria-label={t('common.language')}>
            {LANGUAGE_OPTIONS.map(option => (
              <button
                key={option.value}
                type="button"
                className={language === option.value ? 'is-active' : ''}
                onClick={() => setLanguage(option.value)}
              >
                {t(option.labelKey)}
              </button>
            ))}
          </div>

          <input
            className="input"
            type="email"
            placeholder={t('login.email')}
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />

          <input
            className="input"
            type="password"
            placeholder={t('login.password')}
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          <button type="submit" className="btn btn--primary" disabled={submitting}>
            {submitting ? t('login.signingIn') : t('login.signIn')}
          </button>

          <p className="crm-login-error" role="status">{error}</p>
        </form>
      </section>
    </main>
  )
}

export default Login
