import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['crm.primevent.uz', 'testcrm.primevent.uz', 'syncvista.uz', 'www.syncvista.uz'],
  },
})
