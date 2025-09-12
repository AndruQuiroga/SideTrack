'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiFetch } from '../../../lib/api';

export default function LastfmCallback() {
  const params = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      router.replace('/settings');
      return;
    }
    apiFetch(`/api/auth/lastfm/session?token=${token}`).finally(() => router.replace('/settings'));
  }, [params, router]);

  return <p>Connecting to Last.fm...</p>;
}
