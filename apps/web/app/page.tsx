import Link from 'next/link';
import { fetchScheduledWeeks } from './lib/api/weeks';
import { loadAs } from './lib/server-api';
import { sessionUserId } from './lib/session';
import { PageShell } from './components/page-shell';
import { OverviewContent } from './components/overview';

export const metadata = {
  title: 'SideTrack — Your listening journal',
  description: 'Your listening history and your album club, in one place.',
};
export default async function Home() {
  const userId = await sessionUserId();
  if (!userId)
    return (
      <PageShell
        title="Good music, kept close."
        description="Your listening history and your album club, in one place."
        accent="Welcome"
      >
        <section className="access-state">
          <h2>A place for the records that stay with you.</h2>
          <p>
            Keep your stored listens close. Revisit the albums your club picked, read listener
            notes, and find the conversation in Discord.
          </p>
          <Link href="/login" className="button button-primary">
            Sign in with Discord
          </Link>
          <p className="small muted" style={{ marginTop: 20 }}>
            Club pages are for club members. Personal listening comes from your supported Last.fm
            connection.
          </p>
        </section>
      </PageShell>
    );
  const [club, listening] = await Promise.all([
    loadAs(userId, (api) => fetchScheduledWeeks(api)),
    loadAs(userId, (api, id) => api.getUserRecentListens(id, { limit: 6 })),
  ]);
  return (
    <PageShell
      title="Good music, kept close."
      description="Your listening history and the album club."
      accent="Overview"
    >
      <OverviewContent club={club} listening={listening} />
    </PageShell>
  );
}
