'use client';

import { useState, useEffect } from 'react';

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
    if (errs.length > 0) return;

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
      return;
    }
    setMessage('Settings saved');
  }

  async function handleConnect() {
    const callback = encodeURIComponent(`${window.location.origin}/lastfm/callback`);
    const res = await fetch(`/api/auth/lastfm/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    }
  }

  async function handleDisconnect() {
    await fetch('/api/auth/lastfm/session', { method: 'DELETE' });
    setLfmUser('');
    setLfmConnected(false);
  }

  async function handleSpotifyConnect() {
    const callback = encodeURIComponent(`${window.location.origin}/spotify/callback`);
    const res = await fetch(`/api/auth/spotify/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    }
  }

  async function handleSpotifyDisconnect() {
    await fetch('/api/auth/spotify/disconnect', { method: 'DELETE' });
    setSpUser('');
    setSpConnected(false);
  }

  return (
    <section>
      <h2>Settings</h2>
      {errors.length > 0 && <div role="alert">{errors.join(', ')}</div>}
      {message && <div role="status">{message}</div>}
      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Connect ListenBrainz</legend>
          <label>
            Username
            <input
              placeholder="ListenBrainz username"
              value={lbUser}
              onChange={(e) => setLbUser(e.target.value)}
            />
          </label>
          <label>
            Token
            <input
              placeholder="Token"
              value={lbToken}
              onChange={(e) => setLbToken(e.target.value)}
            />
          </label>
        </fieldset>
        <fieldset>
          <legend>Connect Last.fm</legend>
          {lfmConnected ? (
            <div>
              Connected as {lfmUser}{' '}
              <button type="button" onClick={handleDisconnect}>
                Disconnect
              </button>
            </div>
          ) : (
            <button type="button" onClick={handleConnect}>
              Connect Last.fm
            </button>
          )}
        </fieldset>
        <fieldset>
          <legend>Connect Spotify</legend>
          {spConnected ? (
            <div>
              Connected as {spUser}{' '}
              <button type="button" onClick={handleSpotifyDisconnect}>
                Disconnect
              </button>
            </div>
          ) : (
            <button type="button" onClick={handleSpotifyConnect}>
              Connect Spotify
            </button>
          )}
        </fieldset>
        <fieldset>
          <legend>Options</legend>
          <label>
            <input type="checkbox" checked={useGpu} onChange={(e) => setUseGpu(e.target.checked)} />
            Use GPU
          </label>
          <label>
            <input
              type="checkbox"
              checked={useStems}
              onChange={(e) => setUseStems(e.target.checked)}
            />
            Extract stems
          </label>
          <label>
            <input
              type="checkbox"
              checked={useExcerpts}
              onChange={(e) => setUseExcerpts(e.target.checked)}
            />
            Use excerpts
          </label>
        </fieldset>
        <button type="submit">Save</button>
      </form>
    </section>
  );
}
