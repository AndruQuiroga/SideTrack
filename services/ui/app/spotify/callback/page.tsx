'use client';

import { useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiFetch } from '../../../lib/api';

export default function SpotifyCallback() {
  const params = useSearchParams();
  const router = useRouter();

  const fired = useRef(false);
  useEffect(() => {
    const code = params.get('code');
    if (!code) {
      router.replace('/settings');
      return;
    }
    if (fired.current) return;
    fired.current = true;
    const callback = `${window.location.origin}/spotify/callback`;
    apiFetch(
      `/api/auth/spotify/callback?code=${code}&callback=${encodeURIComponent(callback)}`,
    ).finally(() => router.replace('/settings'));
  }, [params, router]);

  return <p>Connecting to Spotify...</p>;
}
