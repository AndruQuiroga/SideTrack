import Link from 'next/link';
import { PageShell } from './page-shell';
export function FeatureUnavailable({ title, description }: { title: string; description: string }) {
  return (
    <PageShell title={title} accent="Feature availability">
      <section className="access-state">
        <h2>{title} is unavailable</h2>
        <p>{description}</p>
        <div className="actions">
          <Link className="button" href="/">
            Go to Overview
          </Link>
          <Link href="/club/current">Open the album club</Link>
        </div>
      </section>
    </PageShell>
  );
}
