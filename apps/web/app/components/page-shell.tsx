import type { ReactNode } from 'react';

interface PageShellProps {
  title: string;
  description?: string;
  accent?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function PageShell({ title, description, accent, actions, children }: PageShellProps) {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col gap-6 px-4 pb-12 pt-8 lg:px-6 lg:pt-10">
      <section className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          {accent && (
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/80 px-3 py-1 text-xs font-medium text-slate-300 shadow-soft">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
              {accent}
            </div>
          )}
          <h1 className="mt-3 text-balance text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
            {title}
          </h1>
          {description && <p className="mt-2 max-w-2xl text-sm text-slate-300">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </section>
      {children}
    </main>
  );
}
