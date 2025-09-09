'use client';

import { useEffect, useState } from 'react';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { useToast } from '../../components/ToastProvider';

export default function AccountPage() {
  const [user, setUser] = useState('');
  const [lfmUser, setLfmUser] = useState('');
  const [lfmConnected, setLfmConnected] = useState(false);
  const { show } = useToast();

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
    } else {
      show({ title: 'Failed to connect to Last.fm', kind: 'error' });
    }
  }

  async function handleDisconnect() {
    const uid = localStorage.getItem('user_id') || '';
    const res = await fetch('/api/auth/lastfm/session', {
      method: 'DELETE',
      headers: { 'X-User-Id': uid },
    });
    if (!res.ok) {
      show({ title: 'Failed to disconnect Last.fm', kind: 'error' });
      return;
    }
    setLfmConnected(false);
    setLfmUser('');
    show({ title: 'Disconnected from Last.fm', kind: 'success' });
  }

  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-bold">Account</h2>
      <p>Logged in as {user}</p>
      <Card className="space-y-4 p-4">
        <h3 className="text-xl font-semibold">Last.fm</h3>
        {lfmConnected ? (
          <div className="flex items-center gap-2">
            <span>Connected as {lfmUser}</span>
            <Button type="button" onClick={handleDisconnect}>
              Disconnect
            </Button>
          </div>
        ) : (
          <Button type="button" onClick={handleConnect}>
            Connect Last.fm
          </Button>
        )}
      </Card>
    </section>
  );
}
