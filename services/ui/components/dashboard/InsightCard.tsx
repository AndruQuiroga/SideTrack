'use client';

import Link from 'next/link';
import { Card } from '../ui/card';
import type { DashboardInsight } from '../../lib/query';

type Props = {
  insight: DashboardInsight;
};

export default function InsightCard({ insight }: Props) {
  if (insight.error) {
    return (
      <Card variant="glass" className="min-w-[200px] p-4 shadow-soft">
        <div className="text-sm text-rose-400">{insight.error}</div>
      </Card>
    );
  }

  return (
    <Card variant="glass" className="min-w-[200px] p-4 shadow-soft">
      <div className="space-y-2">
        <div className="text-sm font-medium">{insight.summary ?? 'No insight available'}</div>
        {insight.summary && (
          <Link
            href={`/insights?focus=${insight.id}`}
            className="text-xs text-emerald-300 hover:underline"
          >
            View details
          </Link>
        )}
      </div>
    </Card>
  );
}
