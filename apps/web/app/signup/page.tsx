import Link from 'next/link';

import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';

export const metadata = {
  title: 'Sidetrack — Sign up',
  description: 'Create your Sidetrack account and start following friends.',
};

export default function SignupPage() {
  return (
    <PageShell
      title="Create account"
      description="Onboard with Discord or Spotify, pick a handle, and unlock social features."
      accent="Early preview"
      actions={<Link href="/login" className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white">Have an account? Sign in</Link>}
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Step 1" title="Pick a handle" />
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <label className="text-xs uppercase tracking-wide text-slate-400">Display name</label>
            <input
              type="text"
              placeholder="Lydia"
              className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
            />
            <label className="mt-3 block text-xs uppercase tracking-wide text-slate-400">Handle</label>
            <input
              type="text"
              placeholder="@lydia"
              className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
            />
            <button className="mt-4 w-full rounded-xl bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400">
              Continue
            </button>
          </div>
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-300">
            <p className="font-semibold text-white">What happens next</p>
            <ul className="space-y-2">
              <li>• Connect Discord to map your club identity.</li>
              <li>• Optionally link Spotify/Last.fm for now playing and taste graphs.</li>
              <li>• Follow friends and compare compatibility.</li>
            </ul>
            <Link href="/settings" className="text-emerald-200 hover:text-white">
              Skip to linking →
            </Link>
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
