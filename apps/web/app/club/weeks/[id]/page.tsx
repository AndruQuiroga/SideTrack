import { notFound } from 'next/navigation';
import { ApiError } from '@sidetrack/api-client';

import { fetchWeekDetail, type WeekDetailWithRatings } from '../../../lib/api/weeks';
import { WeekDetailPanel } from '../../../components/week-detail';
import { PageShell } from '../../../components/page-shell';
import { Unavailable } from '../../../components/ui';

interface WeekDetailPageProps {
  params: { id: string };
}

export default async function WeekDetailPage({ params }: WeekDetailPageProps) {
  let week: WeekDetailWithRatings;
  try {
    week = await fetchWeekDetail(params.id);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) {
      notFound();
    }
    console.error('Week detail unavailable', error);
    return (
      <PageShell title="Club week" accent="Club archive">
        <Unavailable what="club week" />
      </PageShell>
    );
  }

  return <WeekDetailPanel week={week} />;
}
