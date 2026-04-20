/**
 * RemindmeAI Dark Theme — Design System Tokens
 * Matches the Stitch "Minimal Dark Redesign" specification
 */

export const Colors = {
  // Core backgrounds
  background: '#131313',
  surface: '#1a1a1a',
  surfaceContainer: '#1e1e1e',
  surfaceContainerHigh: '#252525',
  surfaceContainerHighest: '#2c2c2c',

  // Primary (Indigo)
  primary: '#c0c1ff',
  primaryContainer: '#8083ff',
  onPrimary: '#131313',

  // Secondary
  secondary: '#cac4d0',
  secondaryContainer: '#4a4458',

  // Tertiary (Amber)
  tertiary: '#efb842',
  tertiaryContainer: '#815600',

  // Text
  onSurface: '#e6e1e5',
  onSurfaceVariant: '#8e8e93',

  // Status
  error: '#f2b8b5',
  errorContainer: '#8c1d18',
  success: '#4ade80',
  successContainer: '#14532d',

  // Misc
  outline: '#2c2c2c',
  transparent: 'transparent',
} as const;

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const Radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  full: 999,
} as const;

export const Font = {
  regular: { fontFamily: 'Inter_400Regular' as const },
  medium: { fontFamily: 'Inter_500Medium' as const },
  semibold: { fontFamily: 'Inter_600SemiBold' as const },
  bold: { fontFamily: 'Inter_700Bold' as const },
} as const;

export const FontSize = {
  xs: 11,
  sm: 12,
  md: 14,
  lg: 16,
  xl: 18,
  xxl: 22,
  xxxl: 28,
  display: 34,
} as const;

export const API_BASE_URL = 'https://remindmeai-api-6lrc.onrender.com';
