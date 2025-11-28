import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';

const accounts = [
  { name: 'Discord', status: 'Required for club identity', linked: false, cta: 'Link Discord' },
  { name: 'Spotify', status: 'Enables now playing + taste metrics', linked: false, cta: 'Connect Spotify' },
  { name: 'Last.fm', status: 'Pulls scrobbles + history', linked: true, cta: 'Reconnect' },
];

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
        <div className="grid gap-3 md:grid-cols-3">
          {accounts.map((account) => (
            <div key={account.name} className="rounded-2xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-white">{account.name}</p>
                <span
                  className={`rounded-full px-2 py-1 text-[0.7rem] uppercase tracking-wide ${
                    account.linked ? 'bg-emerald-500/20 text-emerald-200' : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {account.linked ? 'Linked' : 'Not linked'}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-400">{account.status}</p>
              <button className="mt-3 w-full rounded-xl bg-slate-800 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500/20 hover:text-emerald-100">
                {account.cta}
              </button>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">
          Linking Spotify or Last.fm unlocks live presence, recommendations, and taste graphs on your profile. Discord is required for club participation.
        </p>
      </Card>
    </PageShell>
  );
}
