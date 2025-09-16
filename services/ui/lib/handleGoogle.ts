import { ApiError, apiFetch } from './api';

type Toast = {
  title: string;
  description?: string;
  kind?: 'success' | 'error' | 'info';
};

type HandleGoogleOpts = {
  next: string | null;
  setUserId: (id: string) => void;
  router: { push: (href: string) => void };
  show: (t: Toast) => void;
};

interface GoogleCallbackResponse {
  credential: string;
}

interface GoogleId {
  initialize(opts: {
    client_id: string;
    callback: (response: GoogleCallbackResponse) => void;
  }): void;
  prompt(): void;
}

interface GoogleGlobal {
  accounts?: { id: GoogleId };
}

interface AuthResponse {
  user_id?: string;
  detail?: string;
}

export async function handleGoogle({ next, setUserId, router, show }: HandleGoogleOpts) {
  const g = (window as unknown as { google?: GoogleGlobal }).google;
  if (!g?.accounts?.id) {
    show({ title: 'Google services unavailable', kind: 'error' });
    return;
  }
  show({ title: 'Signing in with Google…', kind: 'info' });
  g.accounts.id.initialize({
    client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
    callback: async (response: GoogleCallbackResponse) => {
      try {
        const r = await apiFetch('/api/auth/continue/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: response.credential }),
          suppressErrorToast: true,
        });
        const data: AuthResponse = await r.json().catch(() => ({}) as AuthResponse);
        setUserId(data.user_id || '');
        router.push(next || '/');
      } catch (error) {
        const detail =
          error instanceof ApiError
            ? typeof error.payload === 'object' && error.payload && 'detail' in error.payload
              ? (() => {
                  const value = (error.payload as { detail?: unknown }).detail;
                  return typeof value === 'string' && value.trim() ? value : error.message;
                })()
              : error.message
            : error instanceof Error
              ? error.message
              : 'Unable to continue with Google';
        show({ title: detail || 'Unable to continue with Google', kind: 'error' });
      }
    },
  });
  g.accounts.id.prompt();
}
