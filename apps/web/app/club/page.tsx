import { Metadata } from 'next';

import { fetchWeekListWithFallback } from '../../src/api/weeks';
import { PageShell } from '../components/page-shell';
import { ClubGallery } from '../components/club-gallery';

export const metadata: Metadata = {
  title: 'Sidetrack Club — Winners',
  description: 'Browse the archive of Sidetrack Club weeks and winners.',
};

export default async function ClubPage() {
  const weeks = await fetchWeekListWithFallback();
  return (
    <PageShell
      title="Club archive"
      description="Every week of Sidetrack in one place: winners, tags, ratings, filters, and participation stats."
      accent="Live archive + filters"
    >
      <ClubGallery weeks={weeks} />
    </PageShell>
  );
}
