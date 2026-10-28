import { PageShell } from '../../components/page-shell';
import { ClubTabs } from '../../components/club-tabs';
import { SinglesArchive } from '../../components/singles-archive';
import { loadAs } from '../../lib/server-api';
import { sessionUserId } from '../../lib/session';
import { fetchSinglesNights } from '../../lib/api/singles';

export const metadata = { title: 'Singles Night — SideTrack' };
export default async function SinglesPage() {
  const archive = await loadAs(await sessionUserId(), fetchSinglesNights);
  return (
    <PageShell
      title="One song at a time."
      description="Singles Night sessions, first impressions, and final ratings."
      accent="Club / Singles Night"
    >
      <ClubTabs singles />
      <SinglesArchive archive={archive} />
    </PageShell>
  );
}
