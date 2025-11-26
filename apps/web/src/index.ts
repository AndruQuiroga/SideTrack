import { describeProject } from '@sidetrack/shared';

import { fetchWeekDetailWithFallback, fetchWeekListWithFallback } from './api/weeks';
import { renderWinnersGallery } from './ui/winnersGallery';
import { renderWeekDetail } from './ui/weekDetail';

export async function startWebApp(): Promise<void> {
  console.log('Starting web app with shared context:', describeProject());

  const weeks = await fetchWeekListWithFallback();
  const gallery = renderWinnersGallery(weeks);
  console.log('SEO', gallery.metadata);
  console.log(gallery.body);

  const firstWeekId = weeks[0]?.id;
  if (firstWeekId) {
    const weekDetail = await fetchWeekDetailWithFallback(firstWeekId);
    const detailRender = renderWeekDetail(weekDetail);
    console.log('SEO', detailRender.metadata);
    console.log(detailRender.body);
  } else {
    const emptyState = renderWeekDetail(undefined, { error: 'No weeks are available yet.' });
    console.log('SEO', emptyState.metadata);
    console.log(emptyState.body);
  }
}

startWebApp().catch((error) => {
  const failedState = renderWinnersGallery(undefined, { error: 'Failed to start gallery.' });
  console.error('Web app failed to start', error);
  console.log('SEO', failedState.metadata);
  console.log(failedState.body);
});
