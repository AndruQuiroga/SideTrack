'use client';
import { useEffect, useState } from 'react';
import TrajectoryBubble, { TrajectoryData } from './TrajectoryBubble';
import { apiFetch } from '../../lib/api';

export default function TrajectoryClient() {
  const [data, setData] = useState<TrajectoryData>({ points: [], arrows: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiFetch('/dashboard/trajectory');
        const j = await res.json();
        if (!mounted) return;
        setData({ points: j.points ?? [], arrows: j.arrows ?? [] });
      } catch (e) {
        setError('Failed to load trajectory');
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <div className="h-[380px] w-full rounded-lg glass p-3" />;
  if (error) return <div className="text-sm text-rose-400">{error}</div>;
  return <TrajectoryBubble data={data} />;
}
