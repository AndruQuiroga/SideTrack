"use client";

import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

export type Influence = {
  name: string;
  type: string;
  score: number;
  confidence: number;
  trend: number[];
};

type Props = {
  metric?: string;
  window?: string;
  onSelect?: (name: string) => void;
};

export default function InfluencePanel({
  metric = 'energy',
  window = '12w',
  onSelect,
}: Props) {
  const [items, setItems] = useState<Influence[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiFetch(
          `/cohorts/influence?metric=${encodeURIComponent(metric)}&window=${encodeURIComponent(window)}`
        );
        setItems((await res.json()) as Influence[]);
      } catch {
        setItems([]);
      }
    })();
  }, [metric, window]);

  return (
    <aside className="md:w-64 space-y-2">
      <h3 className="text-lg font-semibold">Top Contributors</h3>
      <ul className="divide-y divide-border">
        {items.map((item) => (
          <li
            key={item.name}
            className="cursor-pointer p-2 text-sm hover:bg-muted/20"
            onClick={() => onSelect?.(`${item.type}:${item.name}`)}
          >
            <div className="flex items-center justify-between">
              <span>{item.name}</span>
              <SparkLine values={item.trend} />
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function SparkLine({ values }: { values: number[] }) {
  if (!values.length) return null;
  const max = Math.max(...values);
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = 100 - (v / max) * 100;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <svg viewBox="0 0 100 100" className="h-4 w-10">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        points={points}
      />
    </svg>
  );
}
