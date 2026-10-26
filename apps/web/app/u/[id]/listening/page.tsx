import Link from 'next/link';
import type { RecentListen } from '@sidetrack/api-client';

import { loadAs } from '../../../lib/server-api';
import { sessionUserId } from '../../../lib/session';
import { PageShell } from '../../../components/page-shell';
import { AccessNotice, Card, SectionHeading } from '../../../components/ui';

export const metadata = { title: 'Listening History — Sidetrack' };

const PAGE_SIZE = 50;

const SOURCE_LABELS: Record<string, string> = {
  spotify: 'Spotify',
  lastfm: 'Last.fm',
  listenbrainz: 'ListenBrainz',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function dayKey(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function groupByDay(listens: RecentListen[]): { date: string; items: RecentListen[] }[] {
  const map = new Map<string, RecentListen[]>();
  for (const listen of listens) {
    const key = dayKey(listen.listened_at);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(listen);
  }
  return Array.from(map.entries()).map(([date, items]) => ({ date, items }));
}

interface Props {
  params: { id: string };
  searchParams: { page?: string };
}

export default async function ListeningHistoryPage({ params, searchParams }: Props) {
  const page = Math.max(0, parseInt(searchParams.page ?? '0', 10) || 0);
  // Acts for the session user; the API decides whether they may see this history.
  const result = await loadAs(await sessionUserId(), (api) =>
    api.getUserRecentListens(params.id, { limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
  );
  if (result.state !== 'ok') {
    return (
      <PageShell title="Listening History" accent="History">
        <AccessNotice
          state={result.state === 'not-found' ? 'forbidden' : result.state}
          what="listening history"
          audience="its owner, or club members when the owner shares it"
        />
      </PageShell>
    );
  }
  const listens: RecentListen[] = result.data;

  const groups = groupByDay(listens);
  const hasPrev = page > 0;
  const hasNext = listens.length === PAGE_SIZE;

  return (
    <PageShell
      title="Listening History"
      description={`Full listen log for this user.`}
      accent="History"
      actions={
        <Link
          href={`/u/${params.id}`}
          className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white"
        >
          ← Profile
        </Link>
      }
    >
      {listens.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-400">
            No listening history found. Link Spotify or Last.fm in settings to start tracking.
          </p>
        </Card>
      ) : (
        <div className="space-y-6">
          {groups.map(({ date, items }) => (
            <Card key={date} className="space-y-3">
              <SectionHeading
                eyebrow={`${items.length} ${items.length === 1 ? 'listen' : 'listens'}`}
                title={formatDate(items[0].listened_at)}
              />
              <ul className="space-y-1">
                {items.map((listen, idx) => (
                  <li
                    key={idx}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800/60 bg-slate-900/50 px-3 py-2 text-sm"
                  >
                    <div className="min-w-0 flex-1">
                      <span className="font-medium text-slate-100 truncate block">
                        {listen.track_name}
                      </span>
                      <span className="text-xs text-slate-400">{listen.artist_name}</span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2 text-xs text-slate-500">
                      {listen.source && (
                        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-slate-300">
                          {SOURCE_LABELS[listen.source] ?? listen.source}
                        </span>
                      )}
                      <span>{formatTime(listen.listened_at)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          ))}

          {(hasPrev || hasNext) && (
            <div className="flex justify-between">
              {hasPrev ? (
                <Link
                  href={`/u/${params.id}/listening?page=${page - 1}`}
                  className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                >
                  ← Newer
                </Link>
              ) : (
                <span />
              )}
              {hasNext && (
                <Link
                  href={`/u/${params.id}/listening?page=${page + 1}`}
                  className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                >
                  Older →
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </PageShell>
  );
}
