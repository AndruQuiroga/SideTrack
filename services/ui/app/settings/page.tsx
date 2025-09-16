'use client';

import { useEffect, useState } from 'react';
import SourceCard, { SourceStatus } from '../../components/settings/SourceCard';
import RankerControls from '../../components/settings/RankerControls';
import DataControls from '../../components/settings/DataControls';
import { apiFetch } from '../../lib/api';
import { useAuth } from '../../lib/auth';

interface SourceState {
  spotify: SourceStatus;
  lastfm: SourceStatus;
  lb: SourceStatus;
  mb: SourceStatus;
}

export default function SettingsPage() {
  // Keep hook to ensure auth provider mounts; value unused
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { userId } = useAuth();
  const [connectedUsers, setConnectedUsers] = useState<{ spotify: string; lastfm: string }>({
    spotify: '',
    lastfm: '',
  });
  const [sources, setSources] = useState<SourceState>({
    spotify: 'disconnected',
    lastfm: 'disconnected',
    lb: 'disconnected',
    mb: 'disconnected',
  });

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await apiFetch('/api/settings');
        const data = await res.json().catch(() => ({}));
        if (!active) return;
        setSources({
          spotify: data.spotifyConnected ? 'connected' : 'disconnected',
          lastfm: data.lastfmConnected ? 'connected' : 'disconnected',
          lb: data.listenBrainzUser && data.listenBrainzToken ? 'connected' : 'disconnected',
          mb: 'disconnected',
        });
        setConnectedUsers({
          spotify: data.spotifyUser || '',
          lastfm: data.lastfmUser || '',
        });
      } catch {
        // errors are surfaced through ToastProvider
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-10">
      <section className="space-y-2">
        <div>
          <h2 className="bg-gradient-to-r from-emerald-400 via-cyan-400 to-fuchsia-400 bg-clip-text text-2xl font-extrabold text-transparent">
            Settings
          </h2>
          <p className="text-sm text-muted-foreground">Connect sources and tune your experience</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <SourceCard
            id="spotify"
            name="Spotify"
            scopes={['User library', 'Modify playlists']}
            status={sources.spotify}
            connectedAs={connectedUsers.spotify}
            connectUrl="/api/auth/spotify/login"
            disconnectUrl="/api/auth/spotify/disconnect"
            testUrl="/api/auth/spotify/test"
            onStatusChange={(s) => setSources((prev) => ({ ...prev, spotify: s }))}
          />
          <SourceCard
            id="lastfm"
            name="Last.fm"
            scopes={['Read scrobbles', 'Write scrobbles']}
            status={sources.lastfm}
            connectedAs={connectedUsers.lastfm}
            connectUrl="/api/auth/lastfm/login"
            disconnectUrl="/api/auth/lastfm/session"
            testUrl="/api/settings"
            onStatusChange={(s) => setSources((prev) => ({ ...prev, lastfm: s }))}
          />
          <SourceCard
            id="lb"
            name="ListenBrainz"
            scopes={['Read listens', 'Submit feedback']}
            status={sources.lb}
            connectUrl="/api/auth/lb/login"
            disconnectUrl="/api/auth/lb/disconnect"
            testUrl="/api/auth/lb/test"
            onStatusChange={(s) => setSources((prev) => ({ ...prev, lb: s }))}
          />
          <SourceCard
            id="mb"
            name="MusicBrainz"
            scopes={['Read metadata', 'Submit tags']}
            status={sources.mb}
            connectUrl="/api/auth/mb/login"
            disconnectUrl="/api/auth/mb/disconnect"
            testUrl="/api/auth/mb/test"
            onStatusChange={(s) => setSources((prev) => ({ ...prev, mb: s }))}
          />
        </div>
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold text-foreground/90">Ranker</h3>
        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <div className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br from-violet-400/50 via-fuchsia-400/40 to-pink-400/50 blur-2xl" />
          <RankerControls />
        </div>
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold text-foreground/90">Data</h3>
        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <div className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br from-amber-400/50 via-orange-400/40 to-rose-400/50 blur-2xl" />
          <DataControls />
        </div>
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold text-foreground/90">Danger zone</h3>
        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <div className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br from-rose-500/40 via-red-500/30 to-orange-500/40 blur-2xl" />
          <p className="text-xs text-muted-foreground mb-3">
            Be careful — these actions cannot be undone easily.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-rose-300 hover:bg-white/10"
              onClick={async () => {
                await apiFetch('/api/auth/logout', { method: 'POST' });
                window.location.href = '/login';
              }}
            >
              Log out
            </button>
            <button
              className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-rose-300 hover:bg-white/10"
              onClick={async () => {
                await apiFetch('/api/auth/spotify/disconnect', { method: 'DELETE' }).catch(
                  () => undefined,
                );
                await apiFetch('/api/auth/lastfm/session', { method: 'DELETE' }).catch(
                  () => undefined,
                );
                setSources((s) => ({ ...s, spotify: 'disconnected', lastfm: 'disconnected' }));
              }}
            >
              Disconnect all sources
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
