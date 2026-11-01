import { sessionUserId } from '../../lib/session';
import { loadAs } from '../../lib/server-api';
import { parseAutoplay } from '../../lib/rediscovery';
import { RediscoveryPage } from '../../components/rediscovery';

export const metadata = { title: 'Played a lot, not lately — SideTrack' };

export default async function Rediscover({
  searchParams = {},
}: {
  searchParams?: { autoplay?: string };
}) {
  const userId = await sessionUserId();
  const autoplay = parseAutoplay(searchParams.autoplay);
  const [result, dismissals] = await Promise.all([
    loadAs(userId, (api, id) => api.getRediscovery(id, { include_autoplay: autoplay })),
    loadAs(userId, (api, id) => api.listRediscoveryDismissals(id)),
  ]);
  return <RediscoveryPage result={result} dismissals={dismissals} autoplay={autoplay} />;
}
