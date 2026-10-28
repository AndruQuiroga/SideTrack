import type { SidetrackApiClient, SinglesSessionRead } from '@sidetrack/api-client';

/** Server callers derive the actor from their session before passing this client. */
export async function fetchSinglesNights(api: SidetrackApiClient): Promise<SinglesSessionRead[]> {
  const result: SinglesSessionRead[] = [];
  const limit = 200;
  for (let offset = 0; ; offset += limit) {
    const page = await api.listSinglesNights({ limit, offset });
    result.push(...page);
    if (page.length < limit) return result;
  }
}

export async function fetchSinglesNight(api: SidetrackApiClient, id: string) {
  return api.getSinglesNight(id);
}
