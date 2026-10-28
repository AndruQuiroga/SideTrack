// Synthetic history only. No participant data or production IDs.
const session = {
  id: '11111111-1111-4111-8111-111111111111',
  week_number: 7,
  event_date: '2026-01-14',
  event_at: null,
  original_label: 'WEEK 007 [1-14-2025] - Singles Night',
  source_url: 'https://discord.com/channels/1/100',
  song_count: 1,
  rating_count: 2,
  songs: [
    {
      id: 'song-1',
      title: 'Night Transit',
      artist_name: 'The Paper Satellites',
      url: 'https://example.test/song',
      source_url: 'https://discord.com/channels/1/100/101',
      submissions: [
        {
          user_id: 'user-1',
          display_name: 'Synthetic submitter',
          submitted_at: '2026-01-15T01:00:00Z',
        },
      ],
      ratings: [
        {
          id: 'rating-1',
          user_id: 'user-1',
          display_name: 'Synthetic listener',
          phase: 'first',
          value: 3.5,
          review: 'An immediate favorite.\nThe chorus stays with you.',
          created_at: '2026-01-15T01:00:00Z',
          source_url: 'https://discord.com/channels/1/100/102',
        },
        {
          id: 'rating-2',
          user_id: 'user-2',
          display_name: 'Another listener',
          phase: 'final',
          value: 4.5,
          review: null,
          created_at: '2026-01-15T02:00:00Z',
          source_url: null,
        },
      ],
    },
  ],
};
module.exports = { session };
