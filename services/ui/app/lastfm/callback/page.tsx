'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../lib/auth';
import { apiFetch } from '../../../lib/api';

export default function LastfmCallback() {
  const params = useSearchParams();
  const router = useRouter();
  const { userId } = useAuth();

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      router.replace('/settings');
      return;
    }
    if (!userId) return;
    apiFetch(`/api/auth/lastfm/session?token=${token}`).finally(() => router.replace('/settings'));
  }, [params, router, userId]);

  return <p>Connecting to Last.fm...</p>;
}
