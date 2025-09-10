import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { useToast } from '../ToastProvider';
import { apiFetch } from '../../lib/api';

export type SourceStatus = 'connected' | 'disconnected';

interface SourceCardProps {
  id: string;
  name: string;
  scopes: string[];
  status: SourceStatus;
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
      const callback = encodeURIComponent(`${window.location.origin}/${id}/callback`);
      const res = await apiFetch(`${connectUrl}?callback=${callback}`);
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.url) {
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
      const res = await apiFetch(disconnectUrl, { method: 'DELETE' });
      if (!res.ok) throw new Error('bad');
      setAndNotify('disconnected');
      show({ title: `Disconnected ${name}`, kind: 'success' });
    } catch {
      show({ title: `Failed to disconnect ${name}`, kind: 'error' });
    }
  }

  async function handleTest() {
    try {
      const res = await apiFetch(testUrl);
      if (!res.ok) throw new Error('bad');
      show({ title: `${name} OK`, kind: 'success' });
    } catch {
      show({ title: `${name} test failed`, kind: 'error' });
    }
  }

  return (
    <Card id={id} className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{name}</h3>
        <span
          className={
            status === 'connected'
              ? 'text-emerald-500 text-sm'
              : 'text-rose-500 text-sm'
          }
        >
          {status}
        </span>
      </div>
      <ul className="list-disc pl-5 text-sm">
        {scopes.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <div className="flex gap-2 pt-2">
        {status === 'connected' ? (
          <Button type="button" onClick={handleDisconnect} aria-label={`${name} disconnect`}>
            Disconnect
          </Button>
        ) : (
          <Button type="button" onClick={handleConnect} aria-label={`${name} connect`}>
            Connect
          </Button>
        )}
        <Button
          type="button"
          variant="secondary"
          onClick={handleTest}
          aria-label={`${name} test`}
        >
          Test
        </Button>
      </div>
    </Card>
  );
}

