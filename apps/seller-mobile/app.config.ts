export default {
  expo: {
    name: 'The Textile Care Seller',
    slug: 'the-textile-care-seller',
    version: '1.0.0',
    orientation: 'portrait',
    userInterfaceStyle: 'light',
    icon: './assets/icon.png',
    splash: {
      image: './assets/splash.png',
      resizeMode: 'contain',
      backgroundColor: '#062B5F',
    },
    ios: {
      supportsTablet: true,
    },
    android: {
      adaptiveIcon: {
        foregroundImage: './assets/adaptive-icon.png',
        backgroundColor: '#0887F5',
      },
    },
    web: {
      favicon: './assets/favicon-32x32.png',
    },
    assetBundlePatterns: ['**/*'],
    extra: { apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000' },
  },
};
