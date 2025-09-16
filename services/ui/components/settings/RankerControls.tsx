import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { useToast } from '../ToastProvider';
import { apiFetch } from '../../lib/api';

export default function RankerControls() {
  const { show } = useToast();
  const [discovery, setDiscovery] = useState(0.5);
  const [energy, setEnergy] = useState(0.5);
  const [tempo, setTempo] = useState(120);
  const [avoid, setAvoid] = useState(false);

  async function handleSave() {
    try {
      await apiFetch('/api/ranker/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ discovery, energy, tempo, avoid }),
        suppressErrorToast: true,
      });
      show({ title: 'Ranker settings saved', kind: 'success' });
    } catch {
      show({ title: 'Failed to save ranker settings', kind: 'error' });
    }
  }

  return (
    <Card className="p-4 space-y-4">
      <div>
        <label className="flex flex-col gap-1">
          <span>Discovery vs Familiarity</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={discovery}
            onChange={(e) => setDiscovery(parseFloat(e.target.value))}
          />
        </label>
      </div>
      <div className="flex gap-4">
        <label className="flex flex-col gap-1">
          <span>Target energy</span>
          <Input
            type="number"
            value={energy}
            onChange={(e) => setEnergy(parseFloat(e.target.value))}
            aria-label="target energy"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>Target tempo</span>
          <Input
            type="number"
            value={tempo}
            onChange={(e) => setTempo(parseFloat(e.target.value))}
            aria-label="target tempo"
          />
        </label>
      </div>
      <label className="flex items-center gap-2">
        <Input
          type="checkbox"
          className="h-4 w-4"
          checked={avoid}
          onChange={(e) => setAvoid(e.target.checked)}
          aria-label="avoid repeats"
        />
        <span>Avoid repeats</span>
      </label>
      <Button type="button" onClick={handleSave} aria-label="save ranker">
        Save
      </Button>
    </Card>
  );
}

