import { Metadata } from 'next';

import { fetchWeekList, type WeekDetailWithRatings } from '../lib/api/weeks';
import { PageShell } from '../components/page-shell';
import { ClubGallery } from '../components/club-gallery';
import { Unavailable } from '../components/ui';

export const metadata: Metadata = {
  title: 'Sidetrack Club — Winners',
  description: 'Browse the archive of Sidetrack Club weeks and winners.',
};

export default async function ClubPage() {
  let weeks: WeekDetailWithRatings[] | null = null;
  try {
    weeks = await fetchWeekList();
  } catch (error) {
    console.error('Club archive unavailable', error);
  }
  return (
    <PageShell
      title="Club archive"
      description="Every week of Sidetrack in one place: winners, tags, ratings, filters, and participation stats."
      accent="Live archive + filters"
    >
      {weeks ? <ClubGallery weeks={weeks} /> : <Unavailable what="club archive" />}
    </PageShell>
  );
}
