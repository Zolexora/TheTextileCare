import type { BrandConfiguration } from './types';

export const defaultBrandConfiguration: BrandConfiguration = {
  name: 'The Textile Care',
  theme: {
    primaryColor: '#0f172a',
    secondaryColor: '#f8fafc',
    accentColor: '#0ea5e9',
    fontFamily: 'Inter, sans-serif',
  },
  assets: {
    logo: '/assets/logo.png',
    icon: '/assets/icon.png',
    favicon: '/assets/favicon.ico',
  },
};
