import type { BrandConfiguration } from './types';

export const ttcBrandColors = {
  navy: '#062B5F',
  cyan: '#00A3FF',
  azure: '#0084FF',
  royal: '#0052CC',
  gradientStart: '#0887F5',
  gradientEnd: '#0C3ACF',
  white: '#FFFFFF',
} as const;

export const defaultBrandConfiguration: BrandConfiguration = {
  name: 'The Textile Care',
  theme: {
    primaryColor: '#062B5F',
    secondaryColor: '#f8fafc',
    accentColor: '#00A3FF',
    fontFamily: 'Inter, sans-serif',
  },
  assets: {
    logo: '/logo.png',
    logoWhite: '/logo-white.png',
    logoMark: '/logo-mark.png',
    symbol: '/symbol.png',
    icon: '/icon.png',
    favicon: '/favicon.ico',
    appleTouchIcon: '/apple-touch-icon.png',
    svgLogo: '/logo.svg',
    svgIcon: '/icon.svg',
    svgSymbol: '/symbol.svg',
    manifest: '/site.webmanifest',
  },
};

