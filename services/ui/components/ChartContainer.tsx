import { ReactNode, useState } from 'react';
import { Card } from './ui/card';
import { Dialog, DialogContent } from './ui/dialog';

type Props = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export default function ChartContainer({ title, subtitle, actions, children }: Props) {
  const [open, setOpen] = useState(false);

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
        <div className="min-h-[clamp(120px,25vh,160px)]">
          <div className="hidden h-full w-full md:block">{children}</div>
          <div className="md:hidden">
            <button
              onClick={() => setOpen(true)}
              className="flex h-full w-full items-center justify-center rounded-md border text-sm text-muted-foreground"
            >
              View full chart
            </button>
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogContent className="sm:max-w-md p-4">
                <div className="h-[300px] w-full">{children}</div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </section>
    </Card>
  );
}
