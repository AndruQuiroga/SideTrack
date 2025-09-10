import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { useToast } from '../ToastProvider';
import { apiFetch } from '../../lib/api';

export default function DataControls() {
  const { show } = useToast();
  const [artist, setArtist] = useState('');

  async function resetFeedback() {
    try {
      const res = await apiFetch('/api/feedback/reset', { method: 'POST' });
      if (!res.ok) throw new Error('bad');
      show({ title: 'Feedback reset', kind: 'success' });
    } catch {
      show({ title: 'Failed to reset feedback', kind: 'error' });
    }
  }

  async function forgetArtist() {
    try {
      const res = await apiFetch(`/api/feedback/forget?artist=${encodeURIComponent(artist)}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('bad');
      show({ title: `Forgot ${artist}`, kind: 'success' });
      setArtist('');
    } catch {
      show({ title: 'Failed to forget artist', kind: 'error' });
    }
  }

  async function exportDefaults() {
    try {
      const res = await apiFetch('/api/settings/export');
      if (!res.ok) throw new Error('bad');
      show({ title: 'Exported defaults', kind: 'success' });
    } catch {
      show({ title: 'Failed to export defaults', kind: 'error' });
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <Button type="button" onClick={resetFeedback} aria-label="reset feedback">
        Reset feedback
      </Button>
      <div className="flex gap-2 items-center">
        <Input
          placeholder="Artist name"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          aria-label="artist name"
        />
        <Button type="button" onClick={forgetArtist} aria-label="forget artist">
          Forget
        </Button>
      </div>
      <Button type="button" onClick={exportDefaults} aria-label="export defaults">
        Export defaults
      </Button>
    </Card>
  );
}

