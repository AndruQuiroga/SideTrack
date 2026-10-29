import { PageShell } from '../../components/page-shell';
import { ClubTabs } from '../../components/club-tabs';
import { SinglesGallery } from '../../components/singles-gallery';
import { loadAs } from '../../lib/server-api';
import { sessionUserId } from '../../lib/session';
import { fetchSinglesGallery } from '../../lib/api/singles';
import { loadOlderSinglesNights, retrySinglesNight } from './actions';

export const metadata = { title: 'Singles Night — SideTrack' };
export default async function SinglesPage() {
  const userId = await sessionUserId();
  const gallery = await loadAs(userId, (api) => fetchSinglesGallery(api));
  return (
    <PageShell
      title="Singles Night."
      description="Every pick, night by night."
      accent="Club / Singles Night"
    >
      <ClubTabs singles />
      <SinglesGallery
        key={userId ?? 'signed-out'}
        initial={gallery}
        actions={{ older: loadOlderSinglesNights, retry: retrySinglesNight }}
      />
    </PageShell>
  );
}
