import clsx from 'clsx';
import type { ReactNode } from 'react';
import { safeReturnPath, signInHref } from '../lib/navigation';

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={clsx('section', className)}>{children}</section>;
}
export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={clsx('status-text', className)}>{children}</span>;
}
export function Unavailable({ what, className }: { what: string; className?: string }) {
  return (
    <section className={clsx('access-state', className)} role="status">
      <h2>The {what} is unavailable right now.</h2>
      <p>We couldn&apos;t load this information. Please try again later.</p>
    </section>
  );
}
export function SectionHeading({
  eyebrow,
  title,
  aside,
}: {
  eyebrow?: string;
  title: string;
  aside?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
      </div>
      {aside}
    </div>
  );
}
export function AccessNotice({
  state,
  what,
  audience = 'club members',
  className,
  returnTo = '/',
}: {
  state: 'signed-out' | 'forbidden' | 'unavailable';
  what: string;
  audience?: string;
  className?: string;
  returnTo?: string;
}) {
  if (state === 'unavailable') return <Unavailable what={what} className={className} />;
  return (
    <section className={clsx('access-state', className)}>
      <h2>
        {state === 'signed-out' ? (
          <>Sign in to see the {what}.</>
        ) : (
          <>
            The {what} is for {audience}.
          </>
        )}
      </h2>
      {state === 'signed-out' ? (
        <>
          <p>Use your Discord account to continue. Club membership is managed separately.</p>
          <a className="button button-primary" href={signInHref(safeReturnPath(returnTo))}>
            Sign in with Discord
          </a>
        </>
      ) : (
        <p>Your account doesn&apos;t have access to this information.</p>
      )}
    </section>
  );
}
