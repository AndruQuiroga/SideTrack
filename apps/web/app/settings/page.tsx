import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getServerSession } from 'next-auth/next';

import { authOptions } from '../lib/auth';
import { serverApiBaseUrl, serverApiHeaders } from '../lib/server-env';
import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { ConnectionsGrid } from '../components/connections-grid';

export const metadata = {
  title: 'Sidetrack — Settings',
  description: 'Manage linked accounts and privacy.',
};

type LinkedAccount = { provider: string; username?: string; display_name?: string };

async function fetchLinkedAccounts(userId: string): Promise<LinkedAccount[]> {
  try {
    const res = await fetch(`${serverApiBaseUrl()}/users/${userId}/linked-accounts`, {
      headers: serverApiHeaders(),
      cache: 'no-store',
    });
    if (!res.ok) return [];
    return (await res.json()) as LinkedAccount[];
  } catch {
    return [];
  }
}

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    redirect('/login?from=/settings');
  }

  const linkedAccounts = await fetchLinkedAccounts(session.user.id);
  const isLinked = (provider: string) => linkedAccounts.some((a) => a.provider === provider);

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
        ? `Connected as ${linkedAccounts.find((a) => a.provider === 'lastfm')?.display_name ?? 'unknown'}`
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
        <ConnectionsGrid connections={connections} />
        <p className="text-xs text-slate-400">
          Linking Spotify or Last.fm unlocks live presence, recommendations, and taste graphs on
          your profile. Discord is required for club participation.
        </p>
      </Card>
    </PageShell>
  );
}
