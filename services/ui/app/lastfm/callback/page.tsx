'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiFetch } from '../../../lib/api';

export default function LastfmCallback() {
  const params = useSearchParams();
  const router = useRouter();

  const fired = useRef(false);
  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      router.replace('/settings');
      return;
    }
    if (fired.current) return;
    fired.current = true;
    apiFetch(`/api/auth/lastfm/session?token=${token}`)
      .then(() => {
        // Prime settings so the Settings page reflects connection immediately
        return apiFetch('/api/settings').catch(() => undefined);
      })
      .finally(() => router.replace('/settings'));
  }, [params, router]);

  return <p>Connecting to Last.fm...</p>;
}
