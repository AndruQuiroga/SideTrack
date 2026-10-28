import { Metadata } from 'next';

import { fetchWeekList } from '../lib/api/weeks';
import { loadAs } from '../lib/server-api';
import { sessionUserId } from '../lib/session';
import { PageShell } from '../components/page-shell';
import { ClubArchive } from '../components/club-archive';
import { ClubTabs } from '../components/club-tabs';
import { parseArchiveState } from '../lib/club';

export const metadata: Metadata = {
  title: 'Sidetrack Club — Winners',
  description: 'Browse the archive of Sidetrack Club weeks and winners.',
};

export default async function ClubPage({
  searchParams = {},
}: {
  searchParams?: Record<string, string | string[] | undefined>;
}) {
  const archive = await loadAs(await sessionUserId(), (api) => fetchWeekList(api));
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams))
    if (typeof value === 'string') params.set(key, value);
  return (
    <PageShell
      title="The archive"
      description="Albums we picked. Conversations we kept."
      accent="Club / Archive"
    >
      <ClubTabs archive />
      <ClubArchive archive={archive} initialState={parseArchiveState(params)} />
    </PageShell>
  );
}
