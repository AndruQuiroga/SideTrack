import { notFound } from 'next/navigation';

import { fetchWeekDetail } from '../../../lib/api/weeks';
import { loadAs } from '../../../lib/server-api';
import { sessionUserId } from '../../../lib/session';
import { WeekDetailPanel } from '../../../components/week-detail';
import { PageShell } from '../../../components/page-shell';
import { AccessNotice } from '../../../components/ui';

interface WeekDetailPageProps {
  params: { id: string };
  searchParams?: { from?: string };
}

export default async function WeekDetailPage({ params, searchParams }: WeekDetailPageProps) {
  const week = await loadAs(await sessionUserId(), (api) => fetchWeekDetail(api, params.id));
  if (week.state === 'not-found') notFound();
  if (week.state !== 'ok') {
    return (
      <PageShell title="Club week" accent="Club archive">
        <AccessNotice
          state={week.state}
          what="club week"
          returnTo={`/club/weeks/${encodeURIComponent(params.id)}${searchParams?.from ? `?from=${encodeURIComponent(searchParams.from)}` : ''}`}
        />
      </PageShell>
    );
  }

  return <WeekDetailPanel week={week.data} returnTo={searchParams?.from} />;
}
