'use client';
import { useEffect, useState } from 'react';
import InsightCard, { Insight } from '../../../components/insights/InsightCard';
import InsightModal from '../../../components/insights/InsightModal';
import Skeleton from '../../../components/Skeleton';

export default function InsightsPage() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [active, setActive] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/insights?window=12w')
      .then((r) => r.json())
      .then((d) => setInsights(d))
      .catch(() => setInsights([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Insights</h2>
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {insights.map((ins) => (
            <InsightCard key={ins.ts + ins.type} insight={ins} onClick={() => setActive(ins)} />
          ))}
        </div>
      )}
      <InsightModal insight={active} onOpenChange={(open) => !open && setActive(null)} />
    </section>
  );
}
