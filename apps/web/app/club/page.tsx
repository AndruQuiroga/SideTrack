import { Metadata } from 'next';

import { fetchWeekList } from '../../src/api/weeks';
import { PageShell } from '../components/page-shell';
import { WeekList } from '../components/week-list';

export const metadata: Metadata = {
  title: 'Sidetrack Club — Winners',
  description: 'Browse the archive of Sidetrack Club weeks and winners.',
};

export default async function ClubPage() {
  const weeks = await fetchWeekList();
  return (
    <PageShell
      title="Club archive"
      description="Every week of Sidetrack in one place: winners, tags, ratings, and participation stats."
      accent="Public and mobile friendly"
    >
      <WeekList weeks={weeks} />
    </PageShell>
  );
}
