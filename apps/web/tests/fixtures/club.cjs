const albums = {
  'album-a': {
    id: 'album-a',
    title: 'Soft Geometry',
    artist_name: 'The Parallel Lines',
    release_year: 2024,
    cover_url: null,
  },
  'album-b': {
    id: 'album-b',
    title: 'Night Transit',
    artist_name: 'Mira Vale',
    release_year: 2025,
    cover_url: null,
  },
  'album-c': {
    id: 'album-c',
    title: 'Open Water',
    artist_name: 'Elias North',
    release_year: 2023,
    cover_url: null,
  },
};
function makeWeek(overrides = {}) {
  return {
    id: 'week-42',
    label: 'Week 42',
    week_number: 42,
    created_at: '2026-10-20T00:00:00Z',
    discussion_at: '2026-10-30T02:00:00Z',
    nominations_close_at: '2026-10-26T18:00:00Z',
    poll_close_at: '2026-10-27T18:00:00Z',
    winner_album_id: 'album-b',
    ratings_thread_id: '222222222222222222',
    aggregates: { nomination_count: 2, vote_count: 8, rating_count: 2, rating_average: 4.25 },
    nominations: [
      {
        id: 'nom-a',
        album_id: 'album-a',
        week_id: 'week-42',
        user_id: 'member-a',
        pitch: 'My pitch is not the album title',
        genre: 'Electronic',
        vote_summary: { points: 9, total_votes: 3, first_place: 2, second_place: 1 },
        rating_summary: { count: 0, average: null },
      },
      {
        id: 'nom-b',
        album_id: 'album-b',
        week_id: 'week-42',
        user_id: 'member-b',
        pitch: 'A patient and spacious record.',
        genre: 'Ambient',
        vote_summary: { points: 12, total_votes: 5, first_place: 4, second_place: 1 },
        rating_summary: { count: 2, average: 4.25 },
      },
    ],
    ...overrides,
  };
}
const ratings = [
  {
    id: 'rating-a',
    week_id: 'week-42',
    user_id: 'member-a',
    album_id: 'album-b',
    value: 4.5,
    review:
      'The little details reward a second listen. The closing track changes how the opening feels.',
    favorite_track: 'Northbound',
    created_at: '2026-10-28T12:00:00Z',
  },
  {
    id: 'rating-b',
    week_id: 'week-42',
    user_id: 'member-b',
    album_id: 'album-b',
    value: 4,
    review: 'Patient and spacious. Northbound is the one I keep coming back to.',
    created_at: '2026-10-28T13:00:00Z',
  },
];
const listens = [
  {
    track_name: 'Platform Light',
    artist_name: 'Mira Vale',
    listened_at: '2026-10-28T18:42:00Z',
    source: 'lastfm',
  },
  {
    track_name: 'Low Season',
    artist_name: 'The Parallel Lines',
    listened_at: '2026-10-28T18:36:00Z',
    source: 'lastfm',
  },
  {
    track_name: 'Northbound',
    artist_name: 'Mira Vale',
    listened_at: '2026-10-27T23:59:00Z',
    source: 'lastfm',
  },
];
module.exports = { albums, makeWeek, ratings, listens };
