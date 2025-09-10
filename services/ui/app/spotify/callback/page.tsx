'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../lib/auth';
import { apiFetch } from '../../../lib/api';

export default function SpotifyCallback() {
  const params = useSearchParams();
  const router = useRouter();
  const { userId } = useAuth();

  useEffect(() => {
    const code = params.get('code');
    if (!code) {
      router.replace('/settings');
      return;
    }
    if (!userId) return;
    const callback = encodeURIComponent(`${window.location.origin}/spotify/callback`);
    apiFetch(`/api/auth/spotify/callback?code=${code}&callback=${callback}`).finally(() =>
      router.replace('/settings'),
    );
  }, [params, router, userId]);

  return <p>Connecting to Spotify...</p>;
}
