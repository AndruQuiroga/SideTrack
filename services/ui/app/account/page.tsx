'use client';

import { useEffect, useState } from 'react';

export default function AccountPage() {
  const [user, setUser] = useState('');
  const [lfmUser, setLfmUser] = useState('');
  const [lfmConnected, setLfmConnected] = useState(false);

  useEffect(() => {
    const uid = localStorage.getItem('user_id') || '';
    if (!uid) return;
    fetch('/api/auth/me', { headers: { 'X-User-Id': uid } })
      .then((r) => r.json())
      .then((data) => {
        setUser(data.user_id || '');
        setLfmUser(data.lastfmUser || '');
        setLfmConnected(!!data.lastfmConnected);
      })
      .catch(() => {
        /* ignore */
      });
  }, []);

  async function handleConnect() {
    const callback = encodeURIComponent(`${window.location.origin}/lastfm/callback`);
    const uid = localStorage.getItem('user_id') || '';
    const res = await fetch(`/api/auth/lastfm/login?callback=${callback}`, {
      headers: { 'X-User-Id': uid },
    });
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    }
  }

  async function handleDisconnect() {
    const uid = localStorage.getItem('user_id') || '';
    await fetch('/api/auth/lastfm/session', {
      method: 'DELETE',
      headers: { 'X-User-Id': uid },
    });
    setLfmConnected(false);
    setLfmUser('');
  }

  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-bold">Account</h2>
      <p>Logged in as {user}</p>
      <div>
        <h3 className="text-xl font-semibold">Last.fm</h3>
        {lfmConnected ? (
          <div className="flex items-center gap-2">
            <span>Connected as {lfmUser}</span>
            <button
              type="button"
              onClick={handleDisconnect}
              className="rounded bg-red-500 px-3 py-1 text-white"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={handleConnect}
            className="rounded bg-emerald-500 px-3 py-1 text-white"
          >
            Connect Last.fm
          </button>
        )}
      </div>
    </section>
  );
}
