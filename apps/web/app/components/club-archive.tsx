import type { Access } from '../lib/server-api';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import { ClubGallery } from './club-gallery';
import { AccessNotice } from './ui';
import type { ArchiveState } from '../lib/club';
import { archiveUrl } from '../lib/club';

/** The club archive, or why the visitor can't see it (web/authenticated-pages). */
export function ClubArchive({
  archive,
  initialState,
}: {
  archive: Access<WeekDetailWithRatings[]>;
  initialState?: ArchiveState;
}) {
  if (archive.state === 'ok')
    return <ClubGallery weeks={archive.data} initialState={initialState} />;
  const state = archive.state === 'not-found' ? 'unavailable' : archive.state;
  return (
    <AccessNotice
      state={state}
      what="club archive"
      returnTo={initialState ? archiveUrl(initialState) : '/club'}
    />
  );
}
