'use client';

import { useEffect, useState } from 'react';
import RecList, { type Rec } from '../../components/recs/RecList';
import { apiFetch } from '../../lib/api';

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Rec[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiFetch('/recommendations');
        const j = await r.json();
        setRecs(j.recommendations ?? []);
      } catch {
        setRecs([]);
      }
    })();
  }, []);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Recommendations</h2>
      </div>
      <RecList recs={recs} />
    </section>
  );
}
