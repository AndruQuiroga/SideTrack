'use client';

import { useState, useEffect } from 'react';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { useToast } from '../../components/ToastProvider';

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
  const { show } = useToast();

  useEffect(() => {
    fetch('/api/settings')
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
      });
  }, []);

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
    const res = await fetch('/api/settings', {
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
    const res = await fetch(`/api/auth/lastfm/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    } else {
      show({ title: 'Failed to connect to Last.fm', kind: 'error' });
    }
  }

  async function handleDisconnect() {
    const res = await fetch('/api/auth/lastfm/session', { method: 'DELETE' });
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
    const res = await fetch(`/api/auth/spotify/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    } else {
      show({ title: 'Failed to connect to Spotify', kind: 'error' });
    }
  }

  async function handleSpotifyDisconnect() {
    const res = await fetch('/api/auth/spotify/disconnect', { method: 'DELETE' });
    if (!res.ok) {
      show({ title: 'Failed to disconnect Spotify', kind: 'error' });
      return;
    }
    setSpUser('');
    setSpConnected(false);
    show({ title: 'Disconnected from Spotify', kind: 'success' });
  }

  return (
    <section className="space-y-6">
      <h2>Settings</h2>
      {errors.length > 0 && <div role="alert">{errors.join(', ')}</div>}
      {message && <div role="status">{message}</div>}
      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="space-y-4 p-4">
          <h3 className="text-lg font-semibold">Connect ListenBrainz</h3>
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
        </Card>

        <Card className="space-y-4 p-4">
          <h3 className="text-lg font-semibold">Connect Last.fm</h3>
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

        <Card className="space-y-4 p-4">
          <h3 className="text-lg font-semibold">Connect Spotify</h3>
          {spConnected ? (
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
        </Card>

        <Card className="space-y-4 p-4">
          <h3 className="text-lg font-semibold">Options</h3>
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
        </Card>

        <Button type="submit">Save</Button>
      </form>
    </section>
  );
}
