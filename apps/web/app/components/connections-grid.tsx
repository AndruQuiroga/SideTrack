'use client';

import { requestIntegrationConnect } from '../../src/api/discover';
import { showToast } from './toast';

type Connection = {
  name: 'Discord' | 'Spotify' | 'Last.fm';
  key: 'discord' | 'spotify' | 'lastfm';
  status: string;
  linked: boolean;
  cta: string;
};

const defaultConnections: Connection[] = [
  { name: 'Discord', key: 'discord', status: 'Required for club identity', linked: false, cta: 'Link Discord' },
  { name: 'Spotify', key: 'spotify', status: 'Enables now playing + taste metrics', linked: false, cta: 'Connect Spotify' },
  { name: 'Last.fm', key: 'lastfm', status: 'Pulls scrobbles + history', linked: true, cta: 'Reconnect' },
];

export function ConnectionsGrid({ connections = defaultConnections }: { connections?: Connection[] }) {
  async function onConnect(key: Connection['key']) {
    try {
      const { url } = await requestIntegrationConnect(key);
      if (url) {
        showToast(`Opening ${key} connect…`, 'success');
        window.open(url, '_blank');
      }
    } catch (e) {
      showToast(`Failed to start ${key} connect flow`, 'error');
    }
  }

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {connections.map((account) => (
        <div key={account.name} className="rounded-2xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">
          <div className="flex items-center justify-between">
            <p className="font-semibold text-white">{account.name}</p>
            <span
              className={`rounded-full px-2 py-1 text-[0.7rem] uppercase tracking-wide ${
                account.linked ? 'bg-emerald-500/20 text-emerald-200' : 'bg-slate-800 text-slate-300'
              }`}
            >
              {account.linked ? 'Linked' : 'Not linked'}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">{account.status}</p>
          <button
            onClick={() => onConnect(account.key)}
            className="mt-3 w-full rounded-xl bg-slate-800 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500/20 hover:text-emerald-100"
          >
            {account.cta}
          </button>
        </div>
      ))}
    </div>
  );
}
