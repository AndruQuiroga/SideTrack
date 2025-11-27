import { notFound } from 'next/navigation';

import { fetchWeekDetailWithFallback } from '../../../../src/api/weeks';
import { WeekDetailPanel } from '../../../components/week-detail';

interface WeekDetailPageProps {
  params: { id: string };
}

export default async function WeekDetailPage({ params }: WeekDetailPageProps) {
  const week = await fetchWeekDetailWithFallback(params.id);
  if (!week) {
    notFound();
  }

  return <WeekDetailPanel week={week} />;
}
