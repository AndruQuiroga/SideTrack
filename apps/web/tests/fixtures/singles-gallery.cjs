// Synthetic multi-night coverage. Never derived from real club messages.
const { session } = require('./singles.cjs');
function night(number, count = 6) {
  const event = structuredClone(session);
  event.id = number.toString(16).padStart(8, '0') + '-1111-4111-8111-111111111111';
  event.week_number = number;
  event.event_date = `2026-01-${String(number + 7).padStart(2, '0')}`;
  event.original_label = `Synthetic Singles Night ${number}`;
  event.song_count = count;
  event.rating_count = count;
  event.songs = Array.from({ length: count }, (_, i) => {
    const song = structuredClone(session.songs[0]);
    song.id = `night-${number}-song-${i}`;
    song.title = [
      'Night Transit',
      'Soft Landing',
      'Static Bloom',
      'After the Rain',
      'Good Company',
      'Slow Motion',
      'Under the Stars',
    ][i % 7];
    song.artist_name = ['The Paper Satellites', 'Mira Vale', 'Eastward', 'Low Season'][i % 4];
    song.ratings = song.ratings.filter((r) => r.phase === 'first');
    song.rating_summary = { first: { count: 1, average: 3.5 }, final: { count: 0, average: null } };
    song.cover_url = null;
    song.artwork_source_url = null;
    return song;
  });
  return event;
}
function group(event) {
  return { summary: event, detail: { state: 'ok', data: event } };
}
const currentNights = [7, 6, 5, 4, 3, 2, 1].map((n) => night(n, n >= 6 ? 7 : 6));
const currentBatch = { groups: currentNights.map(group), nextOffset: null };
module.exports = { night, group, currentNights, currentBatch };
