import Link from 'next/link';
import { PageShell } from '../components/page-shell';
import { OAuthButtons } from '../components/oauth-buttons';
import { safeReturnPath } from '../lib/navigation';

export const metadata = {
  title: 'Sign in — SideTrack',
  description: 'Sign in with Discord to access SideTrack.',
};
export default function LoginPage({
  searchParams = {},
}: {
  searchParams?: { error?: string | string[]; from?: string | string[] };
}) {
  return (
    <PageShell
      title="Sign in to SideTrack."
      description="Your listening history and your album club, in one place."
      accent="Account / Sign in"
    >
      <section className="access-state">
        {searchParams.error && (
          <p role="alert" className="inline-error">
            Discord sign-in did not finish. Please try again. If it keeps failing, contact the club
            administrator.
          </p>
        )}
        <OAuthButtons returnTo={safeReturnPath(searchParams.from)} />
        <p className="small muted" style={{ marginTop: 24 }}>
          Sign in with Discord first, then connect Last.fm from{' '}
          <Link href="/settings">Account</Link>. Club pages are available to club members.
        </p>
      </section>
    </PageShell>
  );
}
