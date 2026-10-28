import Link from 'next/link';
import type { RecentListen } from '@sidetrack/api-client';
import type { Access } from '../lib/server-api';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import { latestScheduled } from '../lib/club';
import { AccessNotice, SectionHeading } from './ui';
import { AlbumFeature } from './album-feature';
import { ListenRows } from './listen-rows';

export function OverviewContent({
  club,
  listening,
}: {
  club: Access<WeekDetailWithRatings[]>;
  listening: Access<RecentListen[]>;
}) {
  const week = club.state === 'ok' ? latestScheduled(club.data) : undefined;
  return (
    <>
      {club.state !== 'ok' ? (
        <AccessNotice
          state={club.state === 'not-found' ? 'unavailable' : club.state}
          what="club context"
        />
      ) : week ? (
        <AlbumFeature week={week}>
          <Link href="/club">Browse archive</Link>
        </AlbumFeature>
      ) : (
        <section className="access-state">
          <h2>No weeks have been scheduled</h2>
          <p>Club selections will appear here.</p>
        </section>
      )}
      <section className="section">
        <SectionHeading
          title="Recent listening"
          aside={<Link href="/listening">View history →</Link>}
        />
        <p className="small muted">Stored records · Times shown in UTC</p>
        {listening.state !== 'ok' ? (
          <AccessNotice
            state={listening.state === 'not-found' ? 'unavailable' : listening.state}
            what="recent listening"
            audience="its owner"
            returnTo="/listening"
          />
        ) : listening.data.length ? (
          <ListenRows listens={listening.data} />
        ) : (
          <p className="muted">
            No stored listens. Connect Last.fm from <Link href="/settings">Account</Link>.
          </p>
        )}
      </section>
    </>
  );
}
