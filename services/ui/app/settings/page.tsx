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
  const { userId } = useAuth();
  const [sources, setSources] = useState<SourceState>({
    spotify: 'disconnected',
    lastfm: 'disconnected',
    lb: 'disconnected',
    mb: 'disconnected',
  });

  useEffect(() => {
    if (!userId) return;
    apiFetch('/api/settings')
      .then((r) => r.json())
      .then((data) => {
        setSources({
          spotify: data.spotifyConnected ? 'connected' : 'disconnected',
          lastfm: data.lastfmConnected ? 'connected' : 'disconnected',
          lb:
            data.listenBrainzUser && data.listenBrainzToken
              ? 'connected'
              : 'disconnected',
          mb: 'disconnected',
        });
      })
      .catch(() => {
        /* ignore */
      });
  }, [userId]);

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Sources</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <SourceCard
            id="spotify"
            name="Spotify"
            scopes={['User library', 'Modify playlists']}
            status={sources.spotify}
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
            connectUrl="/api/auth/lastfm/login"
            disconnectUrl="/api/auth/lastfm/session"
            testUrl="/api/auth/lastfm/session"
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
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Ranker</h2>
        <RankerControls />
      </section>
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Data</h2>
        <DataControls />
      </section>
    </div>
  );
}

