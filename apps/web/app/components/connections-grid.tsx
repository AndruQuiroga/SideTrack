'use client';
import { useState } from 'react';
import { requestIntegrationConnect } from '../lib/browser-api';

export type Connection = {
  name: 'Discord' | 'Spotify' | 'Last.fm';
  key: 'discord' | 'spotify' | 'lastfm';
  status: string;
  linked: boolean;
  cta: string;
};
export function ConnectionsGrid({ connections }: { connections: Connection[] | null }) {
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  if (!connections)
    return (
      <section className="access-state" role="status">
        <h2>Connections unavailable</h2>
        <p>Linked accounts are unavailable. Please try again later.</p>
      </section>
    );
  async function connect() {
    setConnecting(true);
    setError(null);
    try {
      const { url } = await requestIntegrationConnect('lastfm');
      if (!url || !/^https:\/\//.test(url)) throw new Error('Missing connection destination');
      window.location.assign(url);
    } catch {
      setError('Could not start the Last.fm connection. Try connecting again.');
      setConnecting(false);
    }
  }
  return (
    <>
      {connections.map((account) => (
        <section key={account.key} className="connection-row">
          <h2>{account.name}</h2>
          <div>
            <strong>
              {account.key === 'spotify'
                ? 'Catalog metadata only'
                : account.linked
                  ? 'Linked'
                  : 'Not linked'}
            </strong>
            <p>
              {account.key === 'spotify'
                ? 'Album details, cover art and links. Personal listening sync is unavailable.'
                : account.status}
            </p>
          </div>
          {account.key === 'lastfm' ? (
            <button className="button" type="button" disabled={connecting} onClick={connect}>
              {connecting ? 'Connecting…' : account.cta}
            </button>
          ) : (
            <span className="small muted">
              {account.key === 'discord' ? 'Identity via sign-in' : 'No linking needed'}
            </span>
          )}
        </section>
      ))}
      {error && (
        <p role="alert" className="inline-error">
          {error}
        </p>
      )}
    </>
  );
}
