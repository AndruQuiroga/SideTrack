'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/button';
import { Switch } from '../ui/switch';
import { Slider } from '../ui/slider';

interface Filters {
  newOnly: boolean;
  freshness: number;
  diversity: number;
  energy: number;
}

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
}

const DEFAULTS: Filters = {
  newOnly: false,
  freshness: 0,
  diversity: 0,
  energy: 0,
};

export default function FiltersBar({ filters, onChange }: Props) {
  const [draft, setDraft] = useState<Filters>(filters);
  const first = useRef(true);
  const timeout = useRef<NodeJS.Timeout>();

  useEffect(() => {
    setDraft(filters);
  }, [filters]);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (timeout.current) clearTimeout(timeout.current);
    timeout.current = setTimeout(() => onChange(draft), 300);
    return () => {
      if (timeout.current) clearTimeout(timeout.current);
    };
  }, [draft, onChange]);

  const apply = () => {
    if (timeout.current) clearTimeout(timeout.current);
    onChange(draft);
  };

  return (
    <div className="space-y-4 text-sm">
      <div className="space-y-2">
        <span className="font-medium">Artist filters</span>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>New artists only</span>
            {draft.newOnly && (
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                On
              </span>
            )}
          </div>
          <Switch
            checked={draft.newOnly}
            onCheckedChange={(checked) => setDraft({ ...draft, newOnly: checked })}
          />
        </div>
      </div>
      <div className="space-y-2">
        <span className="font-medium">Track attributes</span>
        <div className="space-y-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span>Min freshness</span>
              {draft.freshness > DEFAULTS.freshness && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  {draft.freshness.toFixed(1)}
                </span>
              )}
            </div>
            <Slider
              value={[draft.freshness]}
              min={0}
              max={1}
              step={0.1}
              onValueChange={(v) => setDraft({ ...draft, freshness: v[0] })}
            />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span>Diversity</span>
              {draft.diversity > DEFAULTS.diversity && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  {draft.diversity.toFixed(1)}
                </span>
              )}
            </div>
            <Slider
              value={[draft.diversity]}
              min={0}
              max={1}
              step={0.1}
              onValueChange={(v) => setDraft({ ...draft, diversity: v[0] })}
            />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span>Energy</span>
              {draft.energy > DEFAULTS.energy && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  {draft.energy.toFixed(1)}
                </span>
              )}
            </div>
            <Slider
              value={[draft.energy]}
              min={0}
              max={1}
              step={0.1}
              onValueChange={(v) => setDraft({ ...draft, energy: v[0] })}
            />
          </div>
        </div>
      </div>
      <Button type="button" onClick={apply} className="mt-2">
        Apply
      </Button>
    </div>
  );
}
