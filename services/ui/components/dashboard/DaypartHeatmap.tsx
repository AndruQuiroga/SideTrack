'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';
import ChartCard from './ChartCard';

interface Cell {
  day: number;
  hour: number;
  count: number;
  energy: number | null;
  valence: number | null;
  tempo: number | null;
}

interface Highlight {
  day: number;
  hour: number;
  count: number;
  z: number;
}

interface HeatmapResponse {
  cells: Cell[];
  highlights: Highlight[];
}

const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function DaypartHeatmap() {
  const [data, setData] = useState<HeatmapResponse | null>(null);

  useEffect(() => {
    apiFetch('/api/dashboard/daypart/heatmap')
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null));
  }, []);

  const counts: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
  if (data) {
    for (const c of data.cells) {
      counts[c.day][c.hour] = c.count;
    }
  }

  return (
    <div className="space-y-2">
      <ChartCard
        title="Daypart Heatmap"
        subtitle="Listens by day and hour"
        plot={{
          ariaLabel: 'listening heatmap',
          data: [
            {
              z: counts,
              x: Array.from({ length: 24 }, (_, i) => i),
              y: dayNames,
              type: 'heatmap',
              colorscale: 'Viridis',
            },
          ],
        }}
      />
      {data && (
        <>
          <table className="sr-only">
            <caption>Listening counts and averages by day and hour</caption>
            <thead>
              <tr>
                <th>Day</th>
                <th>Hour</th>
                <th>Count</th>
                <th>Energy</th>
                <th>Valence</th>
                <th>Tempo</th>
              </tr>
            </thead>
            <tbody>
              {data.cells.map((c) => (
                <tr key={`${c.day}-${c.hour}`}>
                  <td>{dayNames[c.day]}</td>
                  <td>{c.hour}</td>
                  <td>{c.count}</td>
                  <td>{c.energy?.toFixed(2) ?? ''}</td>
                  <td>{c.valence?.toFixed(2) ?? ''}</td>
                  <td>{c.tempo?.toFixed(1) ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.highlights.length > 0 && (
            <ul className="text-xs">
              {data.highlights.map((h) => (
                <li key={`${h.day}-${h.hour}`}>
                  {dayNames[h.day]} {h.hour}:00 – {h.count} listens
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
