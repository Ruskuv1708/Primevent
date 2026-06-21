import { useOutletContext } from 'react-router-dom'

export type AppLayoutContextValue = {
  currentUser: any
  enabledModules: string[]
  modulesLoaded: boolean
}

export const useAppLayoutContext = () => useOutletContext<AppLayoutContextValue>()
