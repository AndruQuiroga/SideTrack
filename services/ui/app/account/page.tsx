'use client';

import { useEffect, useState } from 'react';
import { Button } from '../../components/ui/button';
import ChartContainer from '../../components/ChartContainer';
import FilterBar from '../../components/FilterBar';
import Skeleton from '../../components/Skeleton';
import { useToast } from '../../components/ToastProvider';
import { useAuth } from '../../lib/auth';
import { apiFetch } from '../../lib/api';

export default function AccountPage() {
  const [user, setUser] = useState('');
  const [lfmUser, setLfmUser] = useState('');
  const [lfmConnected, setLfmConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'profile' | 'lastfm'>('profile');
  const { show } = useToast();
  const { userId } = useAuth();

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    apiFetch('/api/auth/me')
      .then((r) => r.json())
      .then((data) => {
        setUser(data.user_id || '');
        setLfmUser(data.lastfmUser || '');
        setLfmConnected(!!data.lastfmConnected);
      })
      .catch(() => {
        /* ignore */
      })
      .finally(() => setLoading(false));
  }, [userId]);

  async function handleConnect() {
    const callback = `${window.location.origin}/lastfm/callback`;
    const res = await apiFetch(`/api/auth/lastfm/login?callback=${encodeURIComponent(callback)}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    } else {
      show({ title: 'Failed to connect to Last.fm', kind: 'error' });
    }
  }

  async function handleDisconnect() {
    const res = await apiFetch('/api/auth/lastfm/session', {
      method: 'DELETE',
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
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Account</h2>
          <p className="text-sm text-muted-foreground">Manage your profile and connections</p>
        </div>
        <FilterBar
          options={[
            { label: 'Profile', value: 'profile' },
            { label: 'Last.fm', value: 'lastfm' },
          ]}
          value={tab}
          onChange={(v) => setTab(v as 'profile' | 'lastfm')}
        />
      </div>
      {tab === 'profile' ? (
        <ChartContainer title="Profile">
          {loading ? <Skeleton className="h-5 w-40" /> : <p>Logged in as {user}</p>}
        </ChartContainer>
      ) : (
        <ChartContainer title="Last.fm">
          {loading ? (
            <Skeleton className="h-5 w-40" />
          ) : lfmConnected ? (
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
        </ChartContainer>
      )}
    </section>
  );
}
