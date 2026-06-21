import { useEffect, useState } from 'react'

export type UiMode = 'cards' | 'table_1c'

export const UI_MODE_STORAGE_KEY = 'crm_ui_mode'
export const UI_MODE_SESSION_KEY = 'crm_ui_mode_selected_this_session'
const UI_MODE_EVENT = 'crm-ui-mode-change'

const isUiMode = (value: unknown): value is UiMode => value === 'cards' || value === 'table_1c'

export const readStoredUiMode = (): UiMode | null => {
  const raw = localStorage.getItem(UI_MODE_STORAGE_KEY)
  if (!raw) return null
  return isUiMode(raw) ? raw : null
}

export const persistUiMode = (mode: UiMode) => {
  localStorage.setItem(UI_MODE_STORAGE_KEY, mode)
  window.dispatchEvent(new CustomEvent(UI_MODE_EVENT, { detail: mode }))
}

export const isUiModeSelectedInSession = () => sessionStorage.getItem(UI_MODE_SESSION_KEY) === '1'

export const markUiModeSelectedInSession = () => {
  sessionStorage.setItem(UI_MODE_SESSION_KEY, '1')
}

export const resetUiModeSelectionForSession = () => {
  sessionStorage.removeItem(UI_MODE_SESSION_KEY)
}

export const useUiMode = (fallback: UiMode = 'cards') => {
  const [mode, setMode] = useState<UiMode>(() => readStoredUiMode() || fallback)

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== UI_MODE_STORAGE_KEY) return
      if (!event.newValue) return
      if (!isUiMode(event.newValue)) return
      setMode(event.newValue)
    }

    const onInternalModeChange = (event: Event) => {
      const modeValue = (event as CustomEvent<UiMode>).detail
      if (isUiMode(modeValue)) {
        setMode(modeValue)
      }
    }

    window.addEventListener('storage', onStorage)
    window.addEventListener(UI_MODE_EVENT, onInternalModeChange)
    return () => {
      window.removeEventListener('storage', onStorage)
      window.removeEventListener(UI_MODE_EVENT, onInternalModeChange)
    }
  }, [])

  return mode
}

