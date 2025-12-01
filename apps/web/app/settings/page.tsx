import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { ConnectionsGrid } from '../components/connections-grid';

export const metadata = {
  title: 'Sidetrack — Settings',
  description: 'Manage linked accounts and privacy.',
};

export default function SettingsPage() {
  return (
    <PageShell
      title="Account & linking"
      description="Control auth, connected services, and real-time presence."
      accent="Settings"
      actions={<Link href="/login" className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white">Back to login</Link>}
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Connections" title="Linked accounts" />
        <ConnectionsGrid />
        <p className="text-xs text-slate-400">
          Linking Spotify or Last.fm unlocks live presence, recommendations, and taste graphs on your profile. Discord is required for club participation.
        </p>
      </Card>
    </PageShell>
  );
}
