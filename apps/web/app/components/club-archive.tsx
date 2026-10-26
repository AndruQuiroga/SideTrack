import type { Access } from '../lib/server-api';
import type { WeekDetailWithRatings } from '../lib/api/weeks';
import { ClubGallery } from './club-gallery';
import { AccessNotice } from './ui';

/** The club archive, or why the visitor can't see it (web/authenticated-pages). */
export function ClubArchive({ archive }: { archive: Access<WeekDetailWithRatings[]> }) {
  if (archive.state === 'ok') return <ClubGallery weeks={archive.data} />;
  const state = archive.state === 'not-found' ? 'unavailable' : archive.state;
  return <AccessNotice state={state} what="club archive" />;
}
