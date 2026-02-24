import { SidetrackApiClient, TrackFeatureCreate } from '@sidetrack/shared';

import { SpotifyConnector } from '../connectors/spotify';

const AUDIO_FEATURES_URL = 'https://api.spotify.com/v1/audio-features';
const BATCH_SIZE = 100; // Spotify's max for the batch endpoint

interface SpotifyAudioFeature {
  id: string;
  energy: number | null;
  valence: number | null;
  danceability: number | null;
  tempo: number | null;
  acousticness: number | null;
  instrumentalness: number | null;
}

async function fetchAudioFeaturesBatch(
  spotifyIds: string[],
  token: string,
): Promise<SpotifyAudioFeature[]> {
  const res = await fetch(`${AUDIO_FEATURES_URL}?ids=${spotifyIds.join(',')}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = (await res.json()) as { audio_features: (SpotifyAudioFeature | null)[] };
  return (data.audio_features ?? []).filter((f): f is SpotifyAudioFeature => f !== null);
}

export class PopulateFeaturesJob {
  constructor(
    private readonly client: SidetrackApiClient,
    private readonly spotify: SpotifyConnector,
  ) {}

  async run(): Promise<void> {
    const token = await this.spotify.getClientToken();
    if (!token) {
      console.log('[populateFeatures] Spotify client credentials not configured; skipping.');
      return;
    }

    const pending = await this.client.getTracksPendingFeatures(500);
    if (pending.length === 0) return;

    const tracksWithSpotifyId = pending.filter((t) => t.spotify_id);
    console.log(`[populateFeatures] ${tracksWithSpotifyId.length} tracks need audio features.`);

    for (let i = 0; i < tracksWithSpotifyId.length; i += BATCH_SIZE) {
      const batch = tracksWithSpotifyId.slice(i, i + BATCH_SIZE);
      const spotifyIds = batch.map((t) => t.spotify_id!);

      let features: SpotifyAudioFeature[];
      try {
        features = await fetchAudioFeaturesBatch(spotifyIds, token);
      } catch (err) {
        console.error('[populateFeatures] Failed to fetch batch from Spotify', err);
        continue;
      }

      for (const feature of features) {
        const track = batch.find((t) => t.spotify_id === feature.id);
        if (!track) continue;

        const payload: TrackFeatureCreate = {
          energy: feature.energy,
          valence: feature.valence,
          danceability: feature.danceability,
          tempo: feature.tempo,
          acousticness: feature.acousticness,
          instrumentalness: feature.instrumentalness,
        };

        try {
          await this.client.upsertTrackFeatures(track.id, payload);
        } catch (err) {
          console.error(`[populateFeatures] Failed to upsert features for track ${track.id}`, err);
        }
      }
    }

    console.log(`[populateFeatures] Done processing ${tracksWithSpotifyId.length} tracks.`);
  }
}
