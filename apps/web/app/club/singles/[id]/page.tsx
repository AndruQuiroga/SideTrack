import Link from 'next/link';
import { PageShell } from '../../../components/page-shell';
import { ClubTabs } from '../../../components/club-tabs';
import { SinglesDetail } from '../../../components/singles-archive';
import { loadAs } from '../../../lib/server-api';
import { sessionUserId } from '../../../lib/session';
import { fetchSinglesNight } from '../../../lib/api/singles';

export const metadata = { title: 'Singles Night session — SideTrack' };
export default async function SinglesSessionPage({ params }: { params: { id: string } }) {
  const session = await loadAs(await sessionUserId(), (api) => fetchSinglesNight(api, params.id));
  return (
    <PageShell
      title="The songs. The first impressions."
      accent="Club / Singles Night"
      actions={<Link href="/club/singles">All sessions</Link>}
    >
      <ClubTabs singles />
      <SinglesDetail session={session} id={params.id} />
    </PageShell>
  );
}
