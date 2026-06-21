import axios from 'axios'

const CRM_PLATFORM_DEV_API_BASE = 'http://localhost:8007'
const CRM_PLATFORM_EMBEDDED_API_BASE = '/crm-platform-api'
const CRM_PLATFORM_STANDALONE_API_BASE = '/api'

const normalizeApiBase = (value?: string) => {
  const trimmed = (value || '').trim()
  if (!trimmed) return ''
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed
}

const resolveDefaultApiBase = () => {
  if (import.meta.env.DEV) {
    return CRM_PLATFORM_DEV_API_BASE
  }
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/crm_platform')) {
    return CRM_PLATFORM_EMBEDDED_API_BASE
  }
  return CRM_PLATFORM_STANDALONE_API_BASE
}

export const configureCrmPlatformApiBase = () => {
  const apiBase = normalizeApiBase(import.meta.env.VITE_API_BASE_URL || resolveDefaultApiBase())

  if (!apiBase && import.meta.env.PROD) {
    console.error('Missing VITE_API_BASE_URL for production build. Requests may fail.')
  }

  axios.defaults.baseURL = apiBase || (typeof window !== 'undefined' ? window.location.origin : '')
  return axios.defaults.baseURL
}
