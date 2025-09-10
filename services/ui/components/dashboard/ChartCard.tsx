'use client';
import { ReactNode, useState } from 'react';
import Plot from 'react-plotly.js';
import type { Data, Layout, Config } from 'plotly.js';
import { Card } from '../ui/card';
import { Dialog, DialogContent } from '../ui/dialog';

export type PlotProps = {
  data: Data[];
  layout?: Partial<Layout>;
  config?: Partial<Config>;
  ariaLabel: string;
};

type Props = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  plot?: PlotProps;
  children?: ReactNode;
};

export default function ChartCard({ title, subtitle, actions, plot, children }: Props) {
  const [open, setOpen] = useState(false);

  const renderPlot = () => (
    <div tabIndex={0} className="h-full w-full">
      <Plot
        data={plot?.data ?? []}
        layout={{
          autosize: true,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { t: 20, l: 30, r: 10, b: 30 },
          ...plot?.layout,
        }}
        config={{
          displayModeBar: false,
          responsive: true,
          ...plot?.config,
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
        aria-label={plot?.ariaLabel ?? ''}
      />
    </div>
  );

  return (
    <Card asChild variant="glass" className="p-4">
      <section>
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-medium">{title}</h3>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
        <div className="min-h-[clamp(160px,40vh,320px)]">
          {plot ? (
            <>
              <div className="hidden h-full w-full md:block">{renderPlot()}</div>
              <div className="md:hidden">
                <button
                  onClick={() => setOpen(true)}
                  className="flex h-full w-full items-center justify-center rounded-md border text-sm text-muted-foreground"
                >
                  View full chart
                </button>
                <Dialog open={open} onOpenChange={setOpen}>
                  <DialogContent className="sm:max-w-md p-4">
                    <div className="h-[300px] w-full">{renderPlot()}</div>
                  </DialogContent>
                </Dialog>
              </div>
            </>
          ) : (
            children
          )}
        </div>
      </section>
    </Card>
  );
}

