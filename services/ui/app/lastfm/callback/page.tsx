'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../lib/auth';

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
    fetch(`/api/auth/lastfm/session?token=${token}`, {
      headers: { 'X-User-Id': userId },
    }).finally(() => router.replace('/settings'));
  }, [params, router, userId]);

  return <p>Connecting to Last.fm...</p>;
}
