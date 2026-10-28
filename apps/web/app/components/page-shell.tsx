import type { ReactNode } from 'react';

export function PageShell({
  title,
  description,
  accent,
  actions,
  children,
}: {
  title: string;
  description?: string;
  accent?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main id="main-content" className="page-shell">
      <div className="location">SideTrack / {accent ?? title}</div>
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          {description && <p className="page-description">{description}</p>}
        </div>
        {actions && <div className="actions">{actions}</div>}
      </header>
      {children}
      <footer className="page-footer">SideTrack · Music and the people you share it with.</footer>
    </main>
  );
}
