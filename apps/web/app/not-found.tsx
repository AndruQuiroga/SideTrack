import Link from 'next/link';
import { PageShell } from './components/page-shell';
export default function NotFound() {
  return (
    <PageShell title="Page not found." accent="404">
      <section className="access-state">
        <p>We couldn&apos;t find that record or page.</p>
        <Link href="/club" className="button">
          Back to archive
        </Link>
      </section>
    </PageShell>
  );
}
