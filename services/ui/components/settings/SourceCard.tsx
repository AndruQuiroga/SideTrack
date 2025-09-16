import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { useToast } from '../ToastProvider';
import { apiFetch } from '../../lib/api';
import { Radio, Brain, Globe } from 'lucide-react';
import SpotifyIcon from '../common/SpotifyIcon';

export type SourceStatus = 'connected' | 'disconnected';

interface SourceCardProps {
  id: string;
  name: string;
  scopes: string[];
  status: SourceStatus;
  connectedAs?: string;
  connectUrl: string;
  disconnectUrl: string;
  testUrl: string;
  onStatusChange?: (s: SourceStatus) => void;
}

export default function SourceCard({
  id,
  name,
  scopes,
  status: initialStatus,
  connectedAs,
  connectUrl,
  disconnectUrl,
  testUrl,
  onStatusChange,
}: SourceCardProps) {
  const [status, setStatus] = useState<SourceStatus>(initialStatus);
  const { show } = useToast();

  const setAndNotify = (s: SourceStatus) => {
    setStatus(s);
    onStatusChange?.(s);
  };

  async function handleConnect() {
    try {
      const callback = `${window.location.origin}/${id}/callback`;
      const res = await apiFetch(`${connectUrl}?callback=${encodeURIComponent(callback)}`, {
        suppressErrorToast: true,
      });
      const data = await res.json().catch(() => ({}));
      if (data.url) {
        window.location.href = data.url as string;
      } else {
        show({ title: `Failed to connect ${name}`, kind: 'error' });
      }
    } catch {
      show({ title: `Failed to connect ${name}`, kind: 'error' });
    }
  }

  async function handleDisconnect() {
    try {
      await apiFetch(disconnectUrl, { method: 'DELETE', suppressErrorToast: true });
      setAndNotify('disconnected');
      show({ title: `Disconnected ${name}`, kind: 'success' });
    } catch {
      show({ title: `Failed to disconnect ${name}`, kind: 'error' });
    }
  }

  async function handleTest() {
    try {
      const res = await apiFetch(testUrl, { suppressErrorToast: true });
      // Try to reflect connection status when testUrl provides it (e.g. /api/settings)
      try {
        const data = (await res.json()) as {
          lastfmConnected?: boolean;
          spotifyConnected?: boolean;
        };
        if (id === 'lastfm' && typeof data.lastfmConnected === 'boolean') {
          setAndNotify(data.lastfmConnected ? 'connected' : 'disconnected');
        }
        if (id === 'spotify' && typeof data.spotifyConnected === 'boolean') {
          setAndNotify(data.spotifyConnected ? 'connected' : 'disconnected');
        }
      } catch {
        // ignore body parse errors for non-JSON test endpoints
      }
      show({ title: `${name} OK`, kind: 'success' });
    } catch {
      show({ title: `${name} test failed`, kind: 'error' });
    }
  }

  const Icon =
    id === 'spotify' ? SpotifyIcon : id === 'lastfm' ? Radio : id === 'lb' ? Brain : Globe;
  const accent =
    id === 'spotify'
      ? 'from-emerald-400/60 via-teal-400/50 to-cyan-400/60'
      : id === 'lastfm'
        ? 'from-rose-400/60 via-pink-400/50 to-fuchsia-400/60'
        : id === 'lb'
          ? 'from-amber-400/60 via-orange-400/50 to-rose-400/60'
          : 'from-sky-400/60 via-blue-400/50 to-emerald-400/60';

  return (
    <Card id={id} variant="glass" className="relative overflow-hidden p-4">
      <div
        className={`pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-gradient-to-br ${accent} blur-2xl`}
      />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={16} />
          <h3 className="text-sm font-semibold">{name}</h3>
        </div>
        <span
          className={
            status === 'connected'
              ? 'rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-xs text-emerald-300'
              : 'rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-xs text-rose-300'
          }
        >
          {status}
        </span>
      </div>
      {status === 'connected' && connectedAs && (
        <div className="mt-1 text-xs text-muted-foreground">Connected as {connectedAs}</div>
      )}
      <ul className="mt-2 list-disc pl-5 text-xs text-foreground/80">
        {scopes.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        {status === 'connected' ? (
          <Button type="button" onClick={handleDisconnect} aria-label={`${name} disconnect`}>
            Disconnect
          </Button>
        ) : (
          <Button type="button" onClick={handleConnect} aria-label={`${name} connect`}>
            Connect
          </Button>
        )}
        <Button type="button" variant="outline" onClick={handleTest} aria-label={`${name} test`}>
          Test
        </Button>
      </div>
    </Card>
  );
}
