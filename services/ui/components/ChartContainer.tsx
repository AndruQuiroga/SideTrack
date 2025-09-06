import { ReactNode } from 'react';
import { Card } from './ui/card';

type Props = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export default function ChartContainer({ title, subtitle, actions, children }: Props) {
  return (
    <Card asChild variant="glass" className="p-md">
      <section>
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-medium">{title}</h3>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
        <div className="min-h-[160px]">{children}</div>
      </section>
    </Card>
  );
}
