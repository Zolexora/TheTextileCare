export type Environment = 'development' | 'staging' | 'production';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export type HealthStatus = 'ok' | 'degraded' | 'error';
