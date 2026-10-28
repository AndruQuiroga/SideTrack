import { sessionUserId } from '../lib/session';
import { loadAs } from '../lib/server-api';
import { parseListenPage, LISTEN_PAGE_SIZE } from '../lib/listening';
import { ListeningHistory } from '../components/listening-history';

export const metadata = { title: 'Listening history — SideTrack' };
export default async function PersonalListening({
  searchParams = {},
}: {
  searchParams?: { page?: string };
}) {
  const userId = await sessionUserId();
  const page = parseListenPage(searchParams.page);
  const result = await loadAs(userId, (api, id) =>
    api.getUserRecentListens(id, { limit: LISTEN_PAGE_SIZE, offset: page * LISTEN_PAGE_SIZE }),
  );
  return <ListeningHistory result={result} page={page} path="/listening" />;
}
