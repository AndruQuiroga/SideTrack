'use client';
import dynamic from 'next/dynamic';
import { Dialog, DialogContent, DialogTitle } from '../ui/dialog';
import type { Data } from 'plotly.js';
import type { Insight } from './InsightCard';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

type Props = {
  insight: Insight | null;
  onOpenChange: (open: boolean) => void;
};

export default function InsightModal({ insight, onOpenChange }: Props) {
  return (
    <Dialog open={!!insight} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {insight && (
          <>
            <DialogTitle>{insight.summary}</DialogTitle>
            {Array.isArray((insight.details as { data?: unknown } | undefined)?.data) && (
              <Plot
                data={(insight.details as { data?: Data[] } | undefined)?.data ?? []}
                layout={{
                  autosize: true,
                  margin: { t: 20, r: 20, b: 30, l: 30 },
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'transparent',
                  height: 200,
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%', height: '200px' }}
              />
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
