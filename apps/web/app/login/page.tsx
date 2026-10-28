import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { OAuthButtons } from '../components/oauth-buttons';

export const metadata = {
  title: 'Sidetrack — Login',
  description: 'Sign in to unlock profiles, feeds, and linking flows.',
};

export default function LoginPage({
  searchParams,
}: {
  searchParams?: { error?: string | string[] };
}) {
  return (
    <PageShell
      title="Sign in"
      description="Authenticate to access your profile, follow friends, and enable live now-playing data."
      accent="Account"
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Welcome back" title="Sign in with Discord" />
        {searchParams?.error && (
          <p role="alert" className="rounded-xl border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
            Discord sign-in did not finish. Please try again. If it keeps failing, contact the club administrator.
          </p>
        )}
        <OAuthButtons />
        <p className="text-xs text-slate-400">
          Sign in with Discord first, then connect Last.fm from{' '}
          <Link href="/settings" className="text-emerald-200 hover:text-white">Settings</Link>.
        </p>
      </Card>
    </PageShell>
  );
}
