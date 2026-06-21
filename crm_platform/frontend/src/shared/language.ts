import type { TranslationKey } from './i18n'

export type AppLanguage = 'ru' | 'en'

export const LANGUAGE_OPTIONS: Array<{ value: AppLanguage; labelKey: TranslationKey }> = [
  { value: 'ru', labelKey: 'common.russian' },
  { value: 'en', labelKey: 'common.english' },
]

const isAppLanguage = (value: unknown): value is AppLanguage => value === 'ru' || value === 'en'

export const normalizeLanguage = (value: unknown): AppLanguage => (
  isAppLanguage(String(value).toLowerCase()) ? String(value).toLowerCase() as AppLanguage : 'ru'
)
