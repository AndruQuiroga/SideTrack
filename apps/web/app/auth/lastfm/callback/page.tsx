'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';

import { getApiBaseUrl } from '../../../../src/config';
import { PageShell } from '../../../components/page-shell';
import { Card, SectionHeading } from '../../../components/ui';

type CallbackState = 'loading' | 'success' | 'error';

interface CallbackResult {
  status: string;
  provider: string;
  username: string;
  message: string;
}

export default function LastFmCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<CallbackState>('loading');
  const [result, setResult] = useState<CallbackResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');

    if (!token) {
      setState('error');
      setError('No authorization token received from Last.fm');
      return;
    }

    async function completeAuth() {
      try {
        const baseUrl = getApiBaseUrl();
        // TODO: Pass user_id when we have auth context
        const res = await fetch(`${baseUrl}/integrations/lastfm/callback?token=${encodeURIComponent(token!)}`);

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `Authentication failed with status ${res.status}`);
        }

        const data = (await res.json()) as CallbackResult;
        setResult(data);
        setState('success');

        // Redirect to settings after a short delay
        setTimeout(() => {
          router.push('/settings');
        }, 3000);
      } catch (err) {
        setState('error');
        setError(err instanceof Error ? err.message : 'Authentication failed');
      }
    }

    completeAuth();
  }, [searchParams, router]);

  if (state === 'loading') {
    return (
      <PageShell
        title="Connecting Last.fm"
        description="Please wait while we complete the authentication..."
        accent="Authentication"
      >
        <Card className="space-y-4">
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-emerald-400" />
          </div>
          <p className="text-center text-sm text-slate-400">
            Completing Last.fm authentication...
          </p>
        </Card>
      </PageShell>
    );
  }

  if (state === 'error') {
    return (
      <PageShell
        title="Connection Failed"
        description="There was a problem connecting your Last.fm account."
        accent="Error"
      >
        <Card className="space-y-4">
          <SectionHeading eyebrow="Error" title="Authentication Failed" />
          <p className="text-sm text-red-400">{error}</p>
          <div className="flex gap-3">
            <Link
              href="/settings"
              className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
              Back to Settings
            </Link>
            <button
              onClick={() => window.location.reload()}
              className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400"
            >
              Try Again
            </button>
          </div>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Connected!"
      description="Your Last.fm account has been successfully linked."
      accent="Success"
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Success" title="Last.fm Connected" />
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
          <p className="text-sm text-emerald-200">
            Welcome, <span className="font-semibold">{result?.username}</span>!
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {result?.message}
          </p>
        </div>
        <p className="text-sm text-slate-400">
          Redirecting you to settings in a moment...
        </p>
        <Link
          href="/settings"
          className="inline-block rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400"
        >
          Go to Settings Now
        </Link>
      </Card>
    </PageShell>
  );
}
