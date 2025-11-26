import { AxiosError } from 'axios';

export const RETRYABLE_STATUS_CODES = [408, 425, 429, 500, 502, 503, 504] as const;

export function isAxiosError(error: unknown): error is AxiosError {
  return typeof error === 'object' && error !== null && (error as AxiosError).isAxiosError === true;
}

export function isRetryableStatus(status?: number): boolean {
  return status !== undefined && RETRYABLE_STATUS_CODES.includes(status as (typeof RETRYABLE_STATUS_CODES)[number]);
}

export function isNetworkError(error: AxiosError): boolean {
  const code = error.code ?? '';
  return Boolean(code) && ['ECONNABORTED', 'ECONNREFUSED', 'ETIMEDOUT', 'ENETUNREACH', 'EAI_AGAIN'].includes(code);
}

export class ApiError extends Error {
  public status?: number;
  public data?: unknown;
  public isRetryable: boolean;

  constructor(message: string, status?: number, data?: unknown, isRetryable: boolean = false) {
    super(message);
    this.status = status;
    this.data = data;
    this.isRetryable = isRetryable;
    this.name = 'ApiError';
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export function toApiError(error: unknown): ApiError {
  if (isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data;
    const responseDetail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    const message = typeof responseDetail === 'string' ? responseDetail : error.message;

    return new ApiError(message, status, data, isRetryableError(error));
  }

  return new ApiError('Unknown error encountered while calling the API.');
}

export function isRetryableError(error: unknown): boolean {
  if (!isAxiosError(error)) {
    return false;
  }

  return isRetryableStatus(error.response?.status) || (!error.response && isNetworkError(error));
}
