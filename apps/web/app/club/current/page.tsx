import Link from 'next/link';
import { fetchScheduledWeeks } from '../../lib/api/weeks';
import { latestScheduled } from '../../lib/club';
import { loadAs } from '../../lib/server-api';
import { sessionUserId } from '../../lib/session';
import { PageShell } from '../../components/page-shell';
import { ClubTabs } from '../../components/club-tabs';
import { AlbumFeature } from '../../components/album-feature';
import { AccessNotice } from '../../components/ui';

export const metadata = { title: 'Latest scheduled week — SideTrack' };
export default async function CurrentWeekPage() {
  const result = await loadAs(await sessionUserId(), (api) => fetchScheduledWeeks(api));
  const week = result.state === 'ok' ? latestScheduled(result.data) : undefined;
  return (
    <PageShell
      title="This week at the club."
      description="The album, the schedule, and the conversation."
      accent="Club / Latest scheduled week"
    >
      <ClubTabs />
      {result.state !== 'ok' ? (
        <AccessNotice
          state={result.state === 'not-found' ? 'unavailable' : result.state}
          what="club week"
          returnTo="/club/current"
        />
      ) : week ? (
        <AlbumFeature week={week}>
          <Link href="/club">Browse archive</Link>
        </AlbumFeature>
      ) : (
        <section className="access-state">
          <h2>No weeks have been scheduled</h2>
          <p>The next club selection will appear here.</p>
        </section>
      )}
    </PageShell>
  );
}
