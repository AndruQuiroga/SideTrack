import { getApiBaseUrl } from '../config';

export type BlendPreview = {
  name: string;
  description?: string;
  tracks: Array<{ id: string; title: string; artist_name: string; reason?: string }>;
};

export async function createFriendBlend(userA: string, userB: string): Promise<BlendPreview> {
  const res = await fetch(`${getApiBaseUrl()}/playlist/blend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_a: userA, user_b: userB }),
  });
  if (!res.ok) throw new Error(`Blend failed with status ${res.status}`);
  return (await res.json()) as BlendPreview;
}
