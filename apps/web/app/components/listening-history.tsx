import Link from 'next/link';
import type { Route } from 'next';
import type { RecentListen } from '@sidetrack/api-client';
import type { Access } from '../lib/server-api';
import { groupListensByUtcDay, LISTEN_PAGE_SIZE } from '../lib/listening';
import { formatUtc } from '../lib/club';
import { PageShell } from './page-shell';
import { AccessNotice } from './ui';
import { ListenRows } from './listen-rows';

export function ListeningHistory({
  result,
  page,
  path,
  own = true,
}: {
  result: Access<RecentListen[]>;
  page: number;
  path: string;
  own?: boolean;
}) {
  return (
    <PageShell
      title="Listening history"
      description="Available stored listens, in order. Times shown in UTC."
      accent="Listening"
    >
      {result.state !== 'ok' ? (
        <AccessNotice
          state={result.state === 'not-found' ? 'forbidden' : result.state}
          what="listening history"
          audience="its owner, or club members when the owner shares it"
          returnTo={`${path}${page ? `?page=${page}` : ''}`}
        />
      ) : !result.data.length ? (
        <section className="access-state">
          <h2>No stored listens</h2>
          <p>
            {page
              ? 'There are no records on this page.'
              : 'No listening records have been imported here yet.'}
          </p>
          {own && (
            <Link className="button" href="/settings">
              Open Account to connect Last.fm
            </Link>
          )}
        </section>
      ) : (
        groupListensByUtcDay(result.data).map((group) => (
          <section className="section" key={group.date}>
            <h2>{formatUtc(group.date)}</h2>
            <ListenRows listens={group.listens} />
          </section>
        ))
      )}
      {result.state === 'ok' && (
        <nav className="actions" aria-label="Listening pages">
          {page > 0 && (
            <Link className="button" href={`${path}?page=${page - 1}` as Route}>
              ← Newer
            </Link>
          )}
          {result.data.length === LISTEN_PAGE_SIZE && (
            <Link className="button" href={`${path}?page=${page + 1}` as Route}>
              Older →
            </Link>
          )}
        </nav>
      )}
      <p className="small muted" style={{ marginTop: 24 }}>
        This log shows available stored records. Import coverage can be incomplete.
      </p>
    </PageShell>
  );
}
