export default {
  expo: {
    name: 'The Textile Care Marketplace',
    slug: 'the-textile-care-marketplace',
    version: '1.0.0',
    orientation: 'portrait',
    userInterfaceStyle: 'light',
    assetBundlePatterns: ['**/*'],
    extra: { apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000' },
  },
};
