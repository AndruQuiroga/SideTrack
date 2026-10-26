/** Server-only blend generation for the session user. */
import { apiRequest } from '../server-api';

export type BlendPreview = {
  name: string;
  description?: string;
  tracks: Array<{ id: string; title: string; artist_name: string; reason?: string }>;
};

export async function createFriendBlend(
  sessionUserId: string,
  userA: string,
  userB: string,
): Promise<BlendPreview> {
  return apiRequest<BlendPreview>(sessionUserId, '/playlist/blend', {
    method: 'POST',
    body: { user_a: userA, user_b: userB },
  });
}
