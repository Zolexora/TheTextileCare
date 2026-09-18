export default {
  expo: {
    name: 'The Textile Care Seller',
    slug: 'the-textile-care-seller',
    version: '1.0.0',
    orientation: 'portrait',
    userInterfaceStyle: 'light',
    assetBundlePatterns: ['**/*'],
    extra: { apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000' },
  },
};
