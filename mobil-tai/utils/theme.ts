export const Colors = {
  // Brand
  primary: '#E63946',      // The Blue Red kırmızısı
  primaryDark: '#C1121F',
  primaryLight: '#FF6B6B',

  // Backgrounds
  bg: '#0F0F1A',
  bgCard: '#1A1A2E',
  bgInput: '#16213E',
  bgSurface: '#1E2035',

  // Text
  textPrimary: '#F1F1F1',
  textSecondary: '#A0A0B0',
  textMuted: '#6B6B80',

  // Accents
  accent: '#4CC9F0',       // tool-call mavi
  accentGreen: '#06D6A0',  // başarı
  accentOrange: '#F4A261', // uyarı
  accentRed: '#E63946',

  // Borders
  border: '#2A2A3E',
  borderLight: '#3A3A50',

  // Status
  success: '#06D6A0',
  error: '#E63946',
  warning: '#F4A261',
  info: '#4CC9F0',

  // Quote item status
  statusActive: '#06D6A0',
  statusReplaced: '#F4A261',
  statusPassive: '#6B6B80',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 28,
  xxxl: 40,
};

export const Radius = {
  sm: 6,
  md: 10,
  lg: 16,
  xl: 24,
  full: 999,
};

export const Typography = {
  h1: { fontSize: 24, fontWeight: '700' as const, color: Colors.textPrimary },
  h2: { fontSize: 20, fontWeight: '700' as const, color: Colors.textPrimary },
  h3: { fontSize: 16, fontWeight: '600' as const, color: Colors.textPrimary },
  body: { fontSize: 14, fontWeight: '400' as const, color: Colors.textPrimary },
  bodySmall: { fontSize: 12, fontWeight: '400' as const, color: Colors.textSecondary },
  caption: { fontSize: 11, fontWeight: '400' as const, color: Colors.textMuted },
  mono: { fontSize: 12, fontFamily: 'monospace', color: Colors.accent },
};
