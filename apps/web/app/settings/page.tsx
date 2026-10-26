import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getServerSession } from 'next-auth/next';

import { authOptions } from '../lib/auth';
import { fetchLinkedAccounts } from '../lib/api/linked-accounts';
import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { ConnectionsGrid } from '../components/connections-grid';

export const metadata = {
  title: 'Sidetrack — Settings',
  description: 'Manage linked accounts and privacy.',
};

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    redirect('/login?from=/settings');
  }

  const linkedAccounts = await fetchLinkedAccounts(session.user.id);
  const isLinked = (provider: string) =>
    linkedAccounts?.some((a) => a.provider === provider) ?? false;

  const connections = [
    {
      name: 'Discord' as const,
      key: 'discord' as const,
      status: isLinked('discord')
        ? `Signed in as ${session.user.name}`
        : 'Required for club identity',
      linked: isLinked('discord'),
      cta: 'Linked via sign-in',
    },
    {
      name: 'Spotify' as const,
      key: 'spotify' as const,
      status: 'Enables now playing + taste metrics',
      linked: isLinked('spotify'),
      cta: isLinked('spotify') ? 'Reconnect' : 'Connect Spotify',
    },
    {
      name: 'Last.fm' as const,
      key: 'lastfm' as const,
      status: isLinked('lastfm')
        ? `Connected as ${linkedAccounts?.find((a) => a.provider === 'lastfm')?.display_name ?? 'unknown'}`
        : 'Pulls scrobbles + history',
      linked: isLinked('lastfm'),
      cta: isLinked('lastfm') ? 'Reconnect' : 'Connect Last.fm',
    },
  ];

  return (
    <PageShell
      title="Account & linking"
      description="Control auth, connected services, and real-time presence."
      accent="Settings"
      actions={
        <Link
          href={`/u/${session.user.id}`}
          className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white"
        >
          View profile
        </Link>
      }
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Connections" title="Linked accounts" />
        <ConnectionsGrid connections={linkedAccounts === null ? null : connections} />
        <p className="text-xs text-slate-400">
          Linking Spotify or Last.fm unlocks live presence, recommendations, and taste graphs on
          your profile. Discord is required for club participation.
        </p>
      </Card>
    </PageShell>
  );
}
