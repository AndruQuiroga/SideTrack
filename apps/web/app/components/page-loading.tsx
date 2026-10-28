import { PageShell } from './page-shell';
export function PageLoading() {
  return (
    <PageShell title="Loading…" accent="SideTrack">
      <p role="status" className="muted">
        Loading your page…
      </p>
      <div className="loading-line" aria-hidden="true" style={{ width: '65%', marginTop: 24 }} />
      <div className="loading-line" aria-hidden="true" style={{ width: '45%', marginTop: 14 }} />
    </PageShell>
  );
}
