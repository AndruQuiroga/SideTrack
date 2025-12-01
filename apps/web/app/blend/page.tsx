'use client';

import { useState } from 'react';
import { PageShell } from '../components/page-shell';
import { Card, SectionHeading } from '../components/ui';
import { createFriendBlend, type BlendPreview } from '../../src/api/social';
import { showToast } from '../components/toast';

export default function BlendPage() {
  const [userA, setUserA] = useState('demo');
  const [userB, setUserB] = useState('demo2');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<BlendPreview | null>(null);

  async function onBlend() {
    if (!userA || !userB) {
      showToast('Enter two users to create a blend', 'error');
      return;
    }
    setLoading(true);
    setPreview(null);
    try {
      const result = await createFriendBlend(userA, userB);
      setPreview(result);
      showToast('Blend generated!', 'success');
    } catch (e) {
      showToast('Failed to generate blend', 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell
      title="Friend blend"
      description="Create a blended playlist from two users’ tastes."
      accent="Preview"
      actions={
        <button
          onClick={onBlend}
          disabled={loading}
          className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-sidetrack-bg disabled:opacity-60"
        >
          {loading ? 'Blending…' : 'Create blend'}
        </button>
      }
    >
      <Card className="space-y-4">
        <SectionHeading eyebrow="Inputs" title="Pick two users" />
        <div className="grid gap-3 md:grid-cols-2">
          <input
            value={userA}
            onChange={(e) => setUserA(e.target.value)}
            placeholder="User A (id or handle)"
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
          />
          <input
            value={userB}
            onChange={(e) => setUserB(e.target.value)}
            placeholder="User B (id or handle)"
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
          />
        </div>
      </Card>

      <Card className="space-y-3">
        <SectionHeading eyebrow="Result" title={preview?.name ?? 'Blend preview'} />
        {preview ? (
          <div className="space-y-2 text-sm">
            {preview.description && <p className="text-slate-300">{preview.description}</p>}
            <ul className="space-y-2">
              {preview.tracks.map((t) => (
                <li key={t.id} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/60 px-3 py-2">
                  <span className="truncate text-white">{t.title} — <span className="text-slate-300">{t.artist_name}</span></span>
                  {t.reason && <span className="text-xs text-slate-400">{t.reason}</span>}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-slate-400">Choose two users and click Create blend to see a preview.</p>
        )}
      </Card>
    </PageShell>
  );
}
