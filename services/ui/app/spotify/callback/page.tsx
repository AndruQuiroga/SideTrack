'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../lib/auth';

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
    fetch(`/api/auth/spotify/callback?code=${code}&callback=${callback}`, {
      headers: { 'X-User-Id': userId },
    }).finally(() => router.replace('/settings'));
  }, [params, router, userId]);

  return <p>Connecting to Spotify...</p>;
}
