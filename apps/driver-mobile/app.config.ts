export default {
  expo: {
    name: 'The Textile Care Driver',
    slug: 'the-textile-care-driver',
    version: '1.0.0',
    orientation: 'portrait',
    userInterfaceStyle: 'dark',
    assetBundlePatterns: ['**/*'],
    extra: { apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000' },
  },
};
