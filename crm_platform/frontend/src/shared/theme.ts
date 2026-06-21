export const theme = {
  colors: {
    // Primary Colors
    primary: '#0a0a0a',
    primaryDark: '#2a2a2a',

    // Neutrals
    white: '#ffffff',
    black: '#0a0a0a',
    gray: {
      light: '#f3f3f2',
      lighter: '#fafafa',
      border: 'rgba(0, 0, 0, 0.08)',
      text: '#5a5a5a',
      textLight: '#8a8a8a',
      disabled: '#c9c9c7',
    },

    // Status Colors
    status: {
      new: 'rgba(0, 102, 255, 0.10)',
      assigned: 'rgba(0, 102, 255, 0.10)',
      in_process: 'rgba(180, 83, 9, 0.12)',
      pending: 'rgba(185, 28, 28, 0.10)',
      done: 'rgba(21, 128, 61, 0.12)',
    },
    statusText: {
      new: '#0066ff',
      assigned: '#0066ff',
      in_process: '#b45309',
      pending: '#b91c1c',
      done: '#15803d',
    },

    // Priority Colors
    priority: {
      critical: '#b91c1c',
      high: '#b45309',
      medium: '#0066ff',
      low: '#15803d',
    },

    // Semantic
    success: '#15803d',
    warning: '#b45309',
    error: '#b91c1c',
    info: '#0066ff',

    // Role Colors
    roles: {
      superadmin: '#b91c1c',
      admin: '#b45309',
      manager: '#0066ff',
      user: '#15803d',
      viewer: '#8a8a8a',
    },
  },

  typography: {
    xs: '11px',
    sm: '12px',
    base: '13px',
    md: '14px',
    lg: '16px',
    xl: '20px',
    '2xl': '26px',
    '3xl': '32px',
  },

  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
    xxl: '32px',
  },

  borderRadius: {
    sm: '4px',
    md: '6px',
    lg: '8px',
    xl: '12px',
    full: '50%',
  },

  layout: {
    sidebarWidth: '220px',
    toolbarHeight: '48px',
    rowHeight: '40px',
    tableRowHeight: '40px',
    tableHeaderHeight: '32px',
    inputHeight: '32px',
    buttonHeightSm: '28px',
    buttonHeight: '32px',
    buttonHeightLg: '36px',
  },

  motion: {
    easeOut: 'cubic-bezier(0.2, 0, 0, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    durationFast: '120ms',
    durationMed: '180ms',
    durationSlow: '240ms',
  },

  shadows: {
    sm: 'none',
    md: 'none',
    lg: 'none',
  },
}

export default theme
