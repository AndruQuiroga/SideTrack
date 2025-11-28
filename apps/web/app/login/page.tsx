import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';

export const metadata = {
  title: 'Sidetrack — Login',
  description: 'Sign in to unlock profiles, feeds, and linking flows.',
};

export default function LoginPage() {
  return (
    <PageShell
      title="Sign in"
      description="Authenticate to access your profile, follow friends, and enable live now-playing data."
      accent="Auth preview"
      actions={<Link href="/signup" className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white">Create account</Link>}
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Welcome back" title="Choose a sign-in method" />
        <div className="grid gap-3 md:grid-cols-2">
          <button className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:border-emerald-400 hover:text-emerald-100">
            Continue with Discord
          </button>
          <button className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:border-emerald-400 hover:text-emerald-100">
            Continue with Spotify
          </button>
          <button className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:border-emerald-400 hover:text-emerald-100">
            Continue with Last.fm
          </button>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3">
            <label className="text-xs uppercase tracking-wide text-slate-400">Email</label>
            <input
              type="email"
              placeholder="you@example.com"
              className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
            />
            <button className="mt-3 w-full rounded-xl bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400">
              Continue with email
            </button>
          </div>
        </div>
        <p className="text-xs text-slate-400">
          OAuth buttons are wired to the backend in production; for now this is a preview of the flow. You can hop to <Link href="/settings" className="text-emerald-200 hover:text-white">settings</Link>{' '}
          to see linked account states.
        </p>
      </Card>
    </PageShell>
  );
}
