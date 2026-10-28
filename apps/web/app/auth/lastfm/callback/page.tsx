'use client';
import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { completeLastfmLink } from '../../../lib/browser-api';
import { PageShell } from '../../../components/page-shell';

export default function LastFmCallbackPage() {
  const params = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<'loading' | 'success' | 'error'>('loading');
  const [username, setUsername] = useState<string | null>(null);
  useEffect(() => {
    const token = params.get('token'),
      signedState = params.get('state');
    if (!token || !signedState) {
      setState('error');
      return;
    }
    let active = true;
    let redirectTimer: ReturnType<typeof setTimeout> | undefined;
    completeLastfmLink(token, signedState)
      .then(async (response) => {
        if (!response.ok) throw new Error('Connection failed');
        const data = await response.json();
        if (!active) return;
        setUsername(typeof data.username === 'string' ? data.username : null);
        setState('success');
        redirectTimer = setTimeout(() => router.push('/settings'), 3000);
      })
      .catch(() => {
        if (active) setState('error');
      });
    return () => {
      active = false;
      clearTimeout(redirectTimer);
    };
  }, [params, router]);
  return (
    <PageShell
      title={
        state === 'success'
          ? 'Last.fm connected.'
          : state === 'error'
            ? 'Connection did not finish.'
            : 'Connecting Last.fm…'
      }
      accent="Account / Last.fm"
    >
      <section className="access-state">
        {state === 'loading' ? (
          <p role="status">Completing the Last.fm connection…</p>
        ) : state === 'success' ? (
          <>
            <p>{username ? `Connected as ${username}.` : 'Your Last.fm account is linked.'}</p>
            <p className="muted">Returning to Account in a moment.</p>
            <Link className="button" href="/settings">
              Open Account now
            </Link>
          </>
        ) : (
          <>
            <p role="alert" className="inline-error">
              We could not complete the Last.fm connection. Start linking again from Account.
            </p>
            <Link className="button button-primary" href="/settings">
              Back to Account
            </Link>
          </>
        )}
      </section>
    </PageShell>
  );
}
