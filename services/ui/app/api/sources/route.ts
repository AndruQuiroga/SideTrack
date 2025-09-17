import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://sidetrack.network/api';

type SettingsData = {
  spotifyConnected?: boolean;
  lastfmConnected?: boolean;
  listenBrainzUser?: string | null;
  listenBrainzToken?: string | null;
};

export async function GET(req: NextRequest) {
  // Forward auth context to the backend like other API routes
  const headers: Record<string, string> = {};
  const uid = req.headers.get('x-user-id') || req.cookies.get('uid')?.value || '';
  if (uid) headers['X-User-Id'] = uid;
  const at = req.headers.get('authorization') || req.cookies.get('at')?.value || '';
  if (at && !headers['Authorization'])
    headers['Authorization'] = at.startsWith('Bearer ') ? at : `Bearer ${at}`;

  // Fetch settings to derive source connection state
  const r = await fetch(`${API_BASE}/settings`, { headers });
  const data: SettingsData = await r.json().catch(() => ({}) as SettingsData);

  // Map settings into the UI `Source[]` shape
  const sources = [
    {
      type: 'spotify',
      status: data?.spotifyConnected ? 'connected' : 'disconnected',
    },
    {
      type: 'lastfm',
      status: data?.lastfmConnected ? 'connected' : 'disconnected',
    },
    {
      type: 'lb',
      status: data?.listenBrainzUser && data?.listenBrainzToken ? 'connected' : 'disconnected',
    },
    {
      type: 'mb',
      // No MB auth wiring yet; expose as disconnected for now
      status: 'disconnected',
    },
  ];

  return NextResponse.json(sources, { status: 200 });
}
