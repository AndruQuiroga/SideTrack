import { Metadata } from 'next';

import { fetchWeekList } from '../lib/api/weeks';
import { loadAs } from '../lib/server-api';
import { sessionUserId } from '../lib/session';
import { PageShell } from '../components/page-shell';
import { ClubArchive } from '../components/club-archive';

export const metadata: Metadata = {
  title: 'Sidetrack Club — Winners',
  description: 'Browse the archive of Sidetrack Club weeks and winners.',
};

export default async function ClubPage() {
  const archive = await loadAs(await sessionUserId(), (api) => fetchWeekList(api));
  return (
    <PageShell
      title="Club archive"
      description="Every week of Sidetrack in one place: winners, tags, ratings, filters, and participation stats."
      accent="Live archive + filters"
    >
      <ClubArchive archive={archive} />
    </PageShell>
  );
}
