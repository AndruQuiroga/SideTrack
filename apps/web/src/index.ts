import { UUID, describeProject } from '@sidetrack/shared';

import { fetchWeekDetail, fetchWeekList } from './api/weeks';
import { fetchProfileForServer } from './api/profile';
import { renderWinnersGallery } from './ui/winnersGallery';
import { renderWeekDetail } from './ui/weekDetail';
import { renderProfilePage } from './ui/profile';

export async function startWebApp(): Promise<void> {
  console.log('Starting web app with shared context:', describeProject());

  const weeks = await fetchWeekList();
  const gallery = renderWinnersGallery(weeks);
  console.log('SEO', gallery.metadata);
  console.log(gallery.body);

  const firstWeekId = weeks[0]?.id;
  if (firstWeekId) {
    const weekDetail = await fetchWeekDetail(firstWeekId);
    const detailRender = renderWeekDetail(weekDetail);
    console.log('SEO', detailRender.metadata);
    console.log(detailRender.body);
  } else {
    const emptyState = renderWeekDetail(undefined, { error: 'No weeks are available yet.' });
    console.log('SEO', emptyState.metadata);
    console.log(emptyState.body);
  }

  const demoUserId: UUID = (process.env.NEXT_PUBLIC_DEMO_USER_ID as UUID) ?? '00000000-0000-0000-0000-000000000000';
  const profile = await fetchProfileForServer(demoUserId, {
    allowPrivateData: Boolean(process.env.SHOW_PRIVATE_PROFILE),
    workerSyncReady: true,
    range: '30d',
  });
  const profileRender = renderProfilePage(profile);
  console.log('SEO', profileRender.metadata);
  console.log(profileRender.body);
}

startWebApp().catch((error) => {
  const failedState = renderWinnersGallery(undefined, { error: 'Failed to start gallery.' });
  console.error('Web app failed to start', error);
  console.log('SEO', failedState.metadata);
  console.log(failedState.body);
});
