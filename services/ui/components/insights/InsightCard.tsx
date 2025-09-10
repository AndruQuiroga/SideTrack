'use client';
import { Card } from '../ui/card';
import { cn } from '../../lib/utils';

export type Insight = {
  ts: string;
  type: string;
  summary: string;
  details?: Record<string, unknown>;
  severity: number;
};

const TYPE_VARIANTS: Record<string, string> = {
  weekly_listens: 'border-emerald-400',
  discovery: 'border-blue-400',
  surge: 'border-rose-400',
};

type Props = {
  insight: Insight;
  onClick?: () => void;
};

export default function InsightCard({ insight, onClick }: Props) {
  const variant = TYPE_VARIANTS[insight.type] ?? 'border-white/10';
  return (
    <Card
      asChild
      variant="glass"
      className={cn('min-w-[200px] cursor-pointer border p-4', variant)}
    >
      <div onClick={onClick} className="space-y-2">
        <div className="text-sm font-medium">{insight.summary}</div>
        <div className="text-xs text-muted-foreground">
          {new Date(insight.ts).toLocaleDateString()}
        </div>
      </div>
    </Card>
  );
}
