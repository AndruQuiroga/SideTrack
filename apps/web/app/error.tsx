'use client';
import Link from 'next/link';
import { PageShell } from './components/page-shell';
export default function PageError({ reset }: { error: Error; reset: () => void }) {
  return (
    <PageShell title="This page could not load." accent="Request failed">
      <section className="access-state">
        <p role="alert">Something went wrong while loading this page. Please try again.</p>
        <div className="actions">
          <button className="button button-primary" onClick={reset}>
            Try again
          </button>
          <Link href="/">Back to Overview</Link>
        </div>
      </section>
    </PageShell>
  );
}
