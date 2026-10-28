'use client';
import { signIn } from 'next-auth/react';
import { useState } from 'react';
import { safeReturnPath } from '../lib/navigation';

export function OAuthButtons({
  returnTo = '/',
  className = '',
}: {
  returnTo?: string;
  className?: string;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  async function connect() {
    setLoading(true);
    setError(false);
    try {
      await signIn('discord', { callbackUrl: safeReturnPath(returnTo) });
    } catch {
      setError(true);
      setLoading(false);
    }
  }
  return (
    <div className={className}>
      <button className="button button-primary" type="button" onClick={connect} disabled={loading}>
        {loading ? 'Connecting…' : 'Continue with Discord'}
      </button>
      {error && (
        <p role="alert" className="inline-error">
          Discord sign-in did not finish. Please try again.
        </p>
      )}
    </div>
  );
}
