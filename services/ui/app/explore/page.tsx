'use client';
import { useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';
import Tabs from '../../components/explore/Tabs';
import Filters from '../../components/explore/Filters';
import TrajectoryPanel from '../../components/explore/TrajectoryPanel';
import MoodsPanel from '../../components/explore/MoodsPanel';
import RadarPanel from '../../components/explore/RadarPanel';
import OutliersPanel from '../../components/explore/OutliersPanel';

export default function ExplorePage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get('tab') ?? 'trajectory';
  const range = searchParams.get('range') ?? '12w';
  const scrollPositions = useRef<Record<string, number>>({});
  const prevTabRef = useRef(tab);

  const handleTabChange = (next: string, prev: string) => {
    scrollPositions.current[prev] = window.scrollY;
    prevTabRef.current = next;
  };

  useEffect(() => {
    const pos = scrollPositions.current[tab] ?? 0;
    window.scrollTo(0, pos);
  }, [tab]);

  let panel;
  if (tab === 'moods') panel = <MoodsPanel />;
  else if (tab === 'radar') panel = <RadarPanel />;
  else if (tab === 'outliers') panel = <OutliersPanel range={range} />;
  else panel = <TrajectoryPanel />;

  return (
    <section className="space-y-6">
      <Tabs onTabChange={handleTabChange} />
      <Filters />
      {panel}
    </section>
  );
}
