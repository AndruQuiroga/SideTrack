import { notFound } from 'next/navigation';

import { fetchWeekDetail } from '../../../lib/api/weeks';
import { loadAs } from '../../../lib/server-api';
import { sessionUserId } from '../../../lib/session';
import { WeekDetailPanel } from '../../../components/week-detail';
import { PageShell } from '../../../components/page-shell';
import { AccessNotice } from '../../../components/ui';

interface WeekDetailPageProps {
  params: { id: string };
}

export default async function WeekDetailPage({ params }: WeekDetailPageProps) {
  const week = await loadAs(await sessionUserId(), (api) => fetchWeekDetail(api, params.id));
  if (week.state === 'not-found') notFound();
  if (week.state !== 'ok') {
    return (
      <PageShell title="Club week" accent="Club archive">
        <AccessNotice state={week.state} what="club week" />
      </PageShell>
    );
  }

  return <WeekDetailPanel week={week.data} />;
}
