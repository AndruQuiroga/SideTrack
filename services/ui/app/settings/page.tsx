'use client';

import { useState, useEffect } from 'react';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import ChartContainer from '../../components/ChartContainer';
import FilterBar from '../../components/FilterBar';
import Skeleton from '../../components/Skeleton';
import { useToast } from '../../components/ToastProvider';
import { useAuth } from '../../lib/auth';
import { apiFetch } from '../../lib/api';

interface SettingsData {
  listenBrainzUser: string;
  listenBrainzToken: string;
  lastfmUser: string;
  lastfmConnected: boolean;
  spotifyUser: string;
  spotifyConnected: boolean;
  useGpu: boolean;
  useStems: boolean;
  useExcerpts: boolean;
}

export default function Settings() {
  const [lbUser, setLbUser] = useState('');
  const [lbToken, setLbToken] = useState('');
  const [lfmUser, setLfmUser] = useState('');
  const [lfmConnected, setLfmConnected] = useState(false);
  const [spUser, setSpUser] = useState('');
  const [spConnected, setSpConnected] = useState(false);
  const [useGpu, setUseGpu] = useState(false);
  const [useStems, setUseStems] = useState(false);
  const [useExcerpts, setUseExcerpts] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'connections' | 'options'>('connections');
  const { show } = useToast();
  const { userId } = useAuth();

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    apiFetch('/api/settings')
      .then((r) => r.json())
      .then((data: Partial<SettingsData>) => {
        setLbUser(data.listenBrainzUser || '');
        setLbToken(data.listenBrainzToken || '');
        setLfmUser(data.lastfmUser || '');
        setLfmConnected(!!data.lastfmConnected);
        setSpUser(data.spotifyUser || '');
        setSpConnected(!!data.spotifyConnected);
        setUseGpu(!!data.useGpu);
        setUseStems(!!data.useStems);
        setUseExcerpts(!!data.useExcerpts);
      })
      .catch(() => {
        /* ignore */
      })
      .finally(() => setLoading(false));
  }, [userId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs: string[] = [];
    if ((lbUser && !lbToken) || (!lbUser && lbToken)) {
      errs.push('ListenBrainz user and token required together');
    }
    setErrors(errs);
    setMessage('');
    if (errs.length > 0) {
      show({ title: errs.join(', '), kind: 'error' });
      return;
    }

    const body: SettingsData = {
      listenBrainzUser: lbUser,
      listenBrainzToken: lbToken,
      useGpu,
      useStems,
      useExcerpts,
    };
    const res = await apiFetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const serverErrors = Array.isArray(data.detail)
        ? data.detail
        : data.detail
          ? [data.detail]
          : ['Error saving settings'];
      setErrors(serverErrors);
      show({ title: serverErrors.join(', '), kind: 'error' });
      return;
    }
    setMessage('Settings saved');
    show({ title: 'Settings saved', kind: 'success' });
  }

  async function handleConnect() {
    const callback = encodeURIComponent(`${window.location.origin}/lastfm/callback`);
    const res = await apiFetch(`/api/auth/lastfm/login?callback=${callback}`);
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
    setLfmUser('');
    setLfmConnected(false);
    show({ title: 'Disconnected from Last.fm', kind: 'success' });
  }

  async function handleSpotifyConnect() {
    const callback = encodeURIComponent(`${window.location.origin}/spotify/callback`);
    const res = await apiFetch(`/api/auth/spotify/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    } else {
      show({ title: 'Failed to connect to Spotify', kind: 'error' });
    }
  }

  async function handleSpotifyDisconnect() {
    const res = await apiFetch('/api/auth/spotify/disconnect', {
      method: 'DELETE',
    });
    if (!res.ok) {
      show({ title: 'Failed to disconnect Spotify', kind: 'error' });
      return;
    }
    setSpUser('');
    setSpConnected(false);
    show({ title: 'Disconnected from Spotify', kind: 'success' });
  }

  return (
    <section className="@container space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Settings</h2>
          <p className="text-sm text-muted-foreground">Configure integrations and options</p>
        </div>
        <FilterBar
          options={[
            { label: 'Connections', value: 'connections' },
            { label: 'Options', value: 'options' },
          ]}
          value={tab}
          onChange={(v) => setTab(v as 'connections' | 'options')}
        />
      </div>
      {errors.length > 0 && <div role="alert">{errors.join(', ')}</div>}
      {message && <div role="status">{message}</div>}
      <form onSubmit={handleSubmit} className="space-y-6">
        {tab === 'connections' ? (
          <>
            <ChartContainer title="ListenBrainz">
              {loading ? (
                <Skeleton className="h-24" />
              ) : (
                <div className="space-y-2">
                  <div className="space-y-1">
                    <label htmlFor="lb-user" className="text-sm font-medium">
                      Username
                    </label>
                    <Input
                      id="lb-user"
                      placeholder="ListenBrainz username"
                      value={lbUser}
                      onChange={(e) => setLbUser(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label htmlFor="lb-token" className="text-sm font-medium">
                      Token
                    </label>
                    <Input
                      id="lb-token"
                      placeholder="Token"
                      value={lbToken}
                      onChange={(e) => setLbToken(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </ChartContainer>

            <ChartContainer title="Last.fm">
              {loading ? (
                <Skeleton className="h-24" />
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

            <ChartContainer title="Spotify">
              {loading ? (
                <Skeleton className="h-24" />
              ) : spConnected ? (
                <div className="flex items-center gap-2">
                  <span>Connected as {spUser}</span>
                  <Button type="button" onClick={handleSpotifyDisconnect}>
                    Disconnect
                  </Button>
                </div>
              ) : (
                <Button type="button" onClick={handleSpotifyConnect}>
                  Connect Spotify
                </Button>
              )}
            </ChartContainer>
          </>
        ) : (
          <ChartContainer title="Options">
            {loading ? (
              <Skeleton className="h-24" />
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Input
                    id="use-gpu"
                    type="checkbox"
                    className="h-4 w-4"
                    checked={useGpu}
                    onChange={(e) => setUseGpu(e.target.checked)}
                  />
                  <label htmlFor="use-gpu">Use GPU</label>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    id="use-stems"
                    type="checkbox"
                    className="h-4 w-4"
                    checked={useStems}
                    onChange={(e) => setUseStems(e.target.checked)}
                  />
                  <label htmlFor="use-stems">Extract stems</label>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    id="use-excerpts"
                    type="checkbox"
                    className="h-4 w-4"
                    checked={useExcerpts}
                    onChange={(e) => setUseExcerpts(e.target.checked)}
                  />
                  <label htmlFor="use-excerpts">Use excerpts</label>
                </div>
              </div>
            )}
          </ChartContainer>
        )}
        <Button type="submit">Save</Button>
      </form>
    </section>
  );
}
