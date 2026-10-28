import { getServerSession } from 'next-auth/next';
import { authOptions } from '../lib/auth';
import { fetchLinkedAccounts } from '../lib/api/linked-accounts';
import { PageShell } from '../components/page-shell';
import { ConnectionsGrid } from '../components/connections-grid';
import type { Connection } from '../components/connections-grid';
import { AccessNotice } from '../components/ui';

export const metadata = {
  title: 'Connections — SideTrack',
  description: 'Manage your supported account connections.',
};
export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id)
    return (
      <PageShell title="Connections" accent="Account">
        <AccessNotice state="signed-out" what="account connections" returnTo="/settings" />
      </PageShell>
    );
  const accounts = await fetchLinkedAccounts(session.user.id);
  const lastfm = accounts?.find((account) => account.provider === 'lastfm');
  const connections: Connection[] | null =
    accounts === null
      ? null
      : [
          {
            name: 'Discord',
            key: 'discord',
            status: `Signed in as ${session.user.name ?? session.user.handle ?? 'your Discord account'}. Club access is managed separately.`,
            linked: accounts.some((a) => a.provider === 'discord'),
            cta: 'Linked via sign-in',
          },
          {
            name: 'Last.fm',
            key: 'lastfm',
            status: lastfm
              ? `Connected as ${lastfm.display_name ?? lastfm.username ?? 'your Last.fm account'}. Imports supported scrobbles.`
              : 'Imports supported scrobbles into your listening history.',
            linked: Boolean(lastfm),
            cta: lastfm ? 'Reconnect' : 'Connect Last.fm',
          },
          {
            name: 'Spotify',
            key: 'spotify',
            status: 'Catalog metadata only',
            linked: false,
            cta: '',
          },
        ];
  return (
    <PageShell
      title="Connections"
      description="Where your identity and listening records come from."
      accent="Account"
    >
      <ConnectionsGrid connections={connections} />
      <p className="small muted">Connection state does not guarantee complete listening history.</p>
    </PageShell>
  );
}
