'use client';
import { Suspense, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { apiFetch } from '../../lib/api';
import Skeleton from '../Skeleton';

import type { TrajectoryData } from './TrajectoryBubble';

const TrajectoryBubble = dynamic(() => import('./TrajectoryBubble'), {
  loading: () => <Skeleton className="h-[380px]" />,
  ssr: false,
});

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

  if (loading) return <Skeleton className="h-[380px]" />;
  if (error) return <div className="text-sm text-rose-400">{error}</div>;
  return (
    <Suspense fallback={<Skeleton className="h-[380px]" />}>
      <TrajectoryBubble data={data} />
    </Suspense>
  );
}
