'use client';

import { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

export default function LastfmCallback() {
  const params = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = params.get('token');
    if (token) {
      fetch(`/api/auth/lastfm/session?token=${token}`).finally(() => router.replace('/settings'));
    } else {
      router.replace('/settings');
    }
  }, [params, router]);

  return <p>Connecting to Last.fm...</p>;
}
