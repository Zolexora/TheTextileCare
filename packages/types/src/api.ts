import type { ApiError } from './common';

export interface ApiResponse<T> {
  data: T;
  success: true;
  requestId?: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}

export interface ErrorEnvelope {
  error: ApiError;
  requestId?: string;
}
