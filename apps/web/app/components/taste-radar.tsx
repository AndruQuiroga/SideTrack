import React from 'react';
import type { TasteMetric } from '@sidetrack/shared';

type Axis = { id: string; label: string; value: number };

function normalizeMetric(id: string, metric?: TasteMetric): number {
  if (!metric) return 0.5;
  // Map common ids to 0..1
  switch (id) {
    case 'energy':
      return clamp01(metric.value);
    case 'valence':
    case 'mood':
      return clamp01(metric.value);
    case 'danceability':
      return clamp01(metric.value);
    case 'acousticness':
      return clamp01(metric.value);
    case 'tempo':
      // Assume 60..180 BPM typical range
      return clamp01((metric.value - 60) / 120);
    default:
      return clamp01(typeof metric.value === 'number' ? metric.value : 0.5);
  }
}

function clamp01(n: number) {
  return Math.max(0, Math.min(1, n));
}

export function TasteRadar({ metrics }: { metrics: TasteMetric[] }) {
  // Pick up to 3 axes that most UIs recognize
  const energy = metrics.find((m) => m.id === 'energy');
  const valence = metrics.find((m) => m.id === 'valence') ?? metrics.find((m) => m.id === 'mood');
  const dance = metrics.find((m) => m.id === 'danceability') ?? metrics.find((m) => m.id === 'acousticness');

  const axes: Axis[] = [
    { id: 'energy', label: 'Energy', value: normalizeMetric('energy', energy) },
    { id: 'valence', label: 'Valence', value: normalizeMetric('valence', valence) },
    { id: 'danceability', label: dance?.id === 'acousticness' ? 'Acousticness' : 'Danceability', value: normalizeMetric(dance?.id ?? 'danceability', dance) },
  ];

  const size = 140;
  const center = size / 2;
  const radius = size / 2 - 12;
  const points = axes
    .map((axis, i) => {
      const angle = ((Math.PI * 2) / axes.length) * i - Math.PI / 2; // start at top
      const r = radius * axis.value;
      const x = center + r * Math.cos(angle);
      const y = center + r * Math.sin(angle);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="text-emerald-300">
        {/* grid */}
        {[0.33, 0.66, 1].map((f) => (
          <circle key={f} cx={center} cy={center} r={radius * f} fill="none" stroke="rgba(148,163,184,0.2)" />
        ))}
        {/* axes */}
        {axes.map((_, i) => {
          const angle = ((Math.PI * 2) / axes.length) * i - Math.PI / 2;
          const x = center + radius * Math.cos(angle);
          const y = center + radius * Math.sin(angle);
          return <line key={i} x1={center} y1={center} x2={x} y2={y} stroke="rgba(148,163,184,0.2)" />;
        })}
        {/* shape */}
        <polygon points={points} fill="rgba(16,185,129,0.25)" stroke="rgba(16,185,129,0.9)" />
      </svg>
      <ul className="space-y-1 text-xs text-slate-300">
        {axes.map((a) => (
          <li key={a.id} className="flex items-center gap-2">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" /> {a.label}
            <span className="ml-2 rounded-full bg-slate-800 px-2 py-0.5 text-[0.65rem]">{Math.round(a.value * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
