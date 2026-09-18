import { ApiClientError } from './errors';
import type { ApiClientConfig } from './config';

export interface RequestOptions<TBody = unknown> {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: TBody;
  headers?: Record<string, string>;
  timeoutMs?: number;
  requestId?: string;
}

export class ApiClient {
  constructor(private readonly config: ApiClientConfig) {}

  async request<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
    const requestId = options.requestId ?? crypto.randomUUID();
    const controller = new AbortController();
    const timeoutMs = options.timeoutMs ?? this.config.timeoutMs ?? 30000;

    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`${this.config.baseUrl}${path}`, {
        method: options.method ?? 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.config.defaultHeaders,
          ...options.headers,
          'x-request-id': requestId,
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      const payload = response.headers.get('content-type')?.includes('application/json')
        ? await response.json()
        : await response.text();

      if (!response.ok) {
        const errorCode = typeof payload === 'object' && payload && 'error' in payload ? String((payload as any).error.code ?? 'API_ERROR') : 'API_ERROR';
        throw new ApiClientError(typeof payload === 'object' && payload && 'error' in payload ? String((payload as any).error.message ?? 'Request failed') : 'Request failed', {
          status: response.status,
          code: errorCode,
          requestId,
        });
      }

      return payload as TResponse;
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiClientError('Request timed out', { code: 'REQUEST_TIMEOUT', requestId });
      }

      throw new ApiClientError(error instanceof Error ? error.message : 'Request failed', { code: 'REQUEST_FAILED', requestId });
    } finally {
      clearTimeout(timer);
    }
  }
}
