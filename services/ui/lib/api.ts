import { getUserId } from './auth';

type ApiErrorPayload = unknown;

export class ApiError extends Error {
  status: number;
  statusText: string;
  url: string;
  title?: string;
  payload?: ApiErrorPayload;

  constructor({
    message,
    status,
    statusText,
    url,
    title,
    payload,
    cause,
  }: {
    message: string;
    status: number;
    statusText: string;
    url: string;
    title?: string;
    payload?: ApiErrorPayload;
    cause?: unknown;
  }) {
    super(message, { cause });
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.url = url;
    this.title = title;
    this.payload = payload;
  }
}

export type ApiErrorInterceptor = (error: ApiError, context: { url: string; init: RequestInit }) => void;

let errorInterceptor: ApiErrorInterceptor | null = null;

export function setApiErrorInterceptor(fn: ApiErrorInterceptor | null) {
  errorInterceptor = fn;
  return () => {
    if (errorInterceptor === fn) {
      errorInterceptor = null;
    }
  };
}

function getTokenFromCookie(): string {
  if (typeof document === 'undefined') return '';
  const m = document.cookie.match(/(?:^|; )at=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function extractDetail(value: unknown): string | undefined {
  if (value == null) return undefined;
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => extractDetail(item))
      .filter((item): item is string => typeof item === 'string' && item.length > 0);
    return parts.length ? parts.join(', ') : undefined;
  }
  if (typeof value === 'object') {
    const parts = Object.values(value)
      .map((item) => extractDetail(item))
      .filter((item): item is string => typeof item === 'string' && item.length > 0);
    return parts.length ? parts.join(', ') : undefined;
  }
  return String(value);
}

async function parseErrorResponse(res: Response) {
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await res.json();
    } catch {
      return undefined;
    }
  }
  try {
    const text = await res.text();
    return text.length ? text : undefined;
  } catch {
    return undefined;
  }
}

function normalizeError(
  status: number,
  statusText: string,
  payload: ApiErrorPayload,
): { message: string; title?: string } {
  const fallback = statusText || `Request failed with status ${status}`;
  if (!payload) return { message: fallback };
  if (typeof payload === 'string') return { message: payload };
  if (Array.isArray(payload)) {
    const joined = payload
      .map((item) => (typeof item === 'string' ? item : extractDetail(item)))
      .filter((item): item is string => typeof item === 'string' && item.length > 0);
    return { message: joined.length ? joined.join(', ') : fallback };
  }
  if (typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    const title = typeof record.title === 'string' ? record.title : undefined;
    const detailSources: unknown[] = [record.detail, record.message, record.error, record.errors];
    for (const source of detailSources) {
      const detail = extractDetail(source);
      if (detail) {
        return { message: detail, title };
      }
    }
    return { message: fallback, title };
  }
  return { message: fallback };
}

function notifyError(error: ApiError, context: { url: string; init: RequestInit }, suppressToast: boolean) {
  if (!suppressToast && errorInterceptor) {
    errorInterceptor(error, context);
  }
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

export type ApiFetchOptions = RequestInit & { suppressErrorToast?: boolean };

export async function apiFetch(path: string, init: ApiFetchOptions = {}) {
  const { suppressErrorToast = false, ...requestInit } = init;
  const headers = new Headers(requestInit.headers);
  const uid = getUserId();
  if (uid) headers.set('X-User-Id', uid);
  if (!headers.has('Authorization')) {
    const at = getTokenFromCookie();
    if (at) headers.set('Authorization', `Bearer ${at}`);
  }
  const finalInit: RequestInit = { ...requestInit, headers };
  const url = path.startsWith('/api/') ? path : `${API_BASE}${path}`;

  try {
    const res = await fetch(url, finalInit);
    if (!res.ok) {
      const payload = await parseErrorResponse(res);
      const { message, title } = normalizeError(res.status, res.statusText, payload);
      const error = new ApiError({
        message,
        status: res.status,
        statusText: res.statusText,
        url,
        title,
        payload,
      });
      notifyError(error, { url, init: finalInit }, suppressErrorToast);
      throw error;
    }
    return res;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      const error = new ApiError({
        message: 'The request was aborted.',
        status: 0,
        statusText: 'Request aborted',
        url,
        title: 'Request aborted',
        cause: err,
      });
      throw error;
    }
    const error = new ApiError({
      message: err instanceof Error && err.message ? err.message : 'Network error',
      status: 0,
      statusText: 'Network error',
      url,
      title: 'Network error',
      cause: err,
    });
    notifyError(error, { url, init: finalInit }, suppressErrorToast);
    throw error;
  }
}
