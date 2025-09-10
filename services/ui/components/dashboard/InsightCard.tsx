'use client';

import Link from 'next/link';
import { Card } from '../ui/card';

type Insight = {
  id: string;
  summary: string;
};

type Props = {
  insight: Insight;
};

export default function InsightCard({ insight }: Props) {
  return (
    <Card variant="glass" className="min-w-[200px] p-4 shadow-soft">
      <div className="space-y-2">
        <div className="text-sm font-medium">{insight.summary}</div>
        <Link
          href={`/insights?focus=${insight.id}`}
          className="text-xs text-emerald-300 hover:underline"
        >
          View details
        </Link>
      </div>
    </Card>
  );
}

