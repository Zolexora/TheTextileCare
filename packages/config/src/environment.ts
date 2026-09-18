export type RuntimeEnvironment = 'development' | 'test' | 'staging' | 'production';

export interface AppRuntimeConfig {
  environment: RuntimeEnvironment;
  apiBaseUrl: string;
  appName: string;
  isClient: boolean;
}

export function getRuntimeEnvironment(): RuntimeEnvironment {
  const value = process.env.APP_ENV ?? process.env.NODE_ENV ?? 'development';

  if (value === 'production' || value === 'staging' || value === 'test') {
    return value;
  }

  return 'development';
}

export function getRuntimeConfig(): AppRuntimeConfig {
  const environment = getRuntimeEnvironment();

  return {
    environment,
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? 'http://localhost:8000',
    appName: process.env.APP_NAME ?? 'The Textile Care',
    isClient: typeof window !== 'undefined',
  };
}
