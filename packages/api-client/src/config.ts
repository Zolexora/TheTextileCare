export interface ApiClientConfig {
  baseUrl: string;
  timeoutMs?: number;
  defaultHeaders?: Record<string, string>;
}

export const createApiClientConfig = (baseUrl: string, defaultHeaders: Record<string, string> = {}): ApiClientConfig => ({
  baseUrl,
  timeoutMs: 30000,
  defaultHeaders,
});
