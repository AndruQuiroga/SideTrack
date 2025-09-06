'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

export default function SpotifyCallback() {
  const params = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const code = params.get('code');
    if (code) {
      const callback = encodeURIComponent(`${window.location.origin}/spotify/callback`);
      fetch(`/api/auth/spotify/callback?code=${code}&callback=${callback}`)
        .finally(() => router.replace('/settings'));
    } else {
      router.replace('/settings');
    }
  }, [params, router]);

  return <p>Connecting to Spotify...</p>;
}
