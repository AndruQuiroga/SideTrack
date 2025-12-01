'use client';

import { useState } from 'react';
import { requestIntegrationConnect } from '../../src/api/discover';
import { showToast } from './toast';

type Provider = 'discord' | 'spotify' | 'lastfm';

interface OAuthButtonProps {
  provider: Provider;
  label: string;
  className?: string;
}

const providerLabels: Record<Provider, string> = {
  discord: 'Discord',
  spotify: 'Spotify',
  lastfm: 'Last.fm',
};

export function OAuthButton({ provider, label, className = '' }: OAuthButtonProps) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    try {
      const { url } = await requestIntegrationConnect(provider);
      if (url) {
        showToast(`Opening ${providerLabels[provider]} connect…`, 'success');
        window.location.href = url;
      } else {
        showToast(`No redirect URL received for ${providerLabels[provider]}`, 'error');
      }
    } catch (e) {
      showToast(`Failed to start ${providerLabels[provider]} connect flow`, 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={`rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:border-emerald-400 hover:text-emerald-100 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400" />
          Connecting...
        </span>
      ) : (
        label
      )}
    </button>
  );
}

interface OAuthButtonsProps {
  className?: string;
}

export function OAuthButtons({ className = '' }: OAuthButtonsProps) {
  return (
    <div className={`grid gap-3 md:grid-cols-2 ${className}`}>
      <OAuthButton provider="discord" label="Continue with Discord" />
      <OAuthButton provider="spotify" label="Continue with Spotify" />
      <OAuthButton provider="lastfm" label="Continue with Last.fm" />
    </div>
  );
}
