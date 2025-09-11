import { NextRequest, NextResponse } from 'next/server';

/**
 * Fetch artwork URLs for given track identifiers. Results are cached by
 * Next.js' built-in fetch caching to avoid repeated lookups.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const spotifyId = searchParams.get('spotify_id');
  const recordingMbid = searchParams.get('recording_mbid');

  let url: string | null = null;

  try {
    if (spotifyId) {
      const r = await fetch(
        `https://open.spotify.com/oembed?url=spotify:track:${spotifyId}`,
        { next: { revalidate: 60 * 60 * 24 } },
      );
      const j = await r.json();
      url = j?.thumbnail_url ?? null;
    } else if (recordingMbid) {
      const r = await fetch(
        `https://coverartarchive.org/release/${recordingMbid}/front`,
        { next: { revalidate: 60 * 60 * 24 } },
      );
      if (r.ok) {
        // coverartarchive returns the image directly
        url = r.url;
      }
    }
  } catch {
    // Ignore errors and return null
  }

  return NextResponse.json({ url });
}

