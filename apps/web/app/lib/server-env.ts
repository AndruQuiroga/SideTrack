/**
 * Server-only configuration. Never import this from a client component: it reads files
 * and returns the web app's API token.
 */
import { readFileSync } from 'node:fs';

type Env = Record<string, string | undefined>;

/** Header naming the user an API call acts for (ADR 0009). */
export const ACT_AS_HEADER = 'X-Sidetrack-Act-As';

/**
 * Read `name` from the environment, or from the file named by `${name}_FILE`
 * (Docker/Swarm secrets). A trailing newline in the file is dropped.
 */
export function readSecret(
  name: string,
  env: Env = process.env,
  readFile: (path: string) => string = (path) => readFileSync(path, 'utf8'),
): string | undefined {
  const direct = env[name];
  if (direct) return direct;
  const file = env[`${name}_FILE`];
  if (!file) return undefined;
  return readFile(file).replace(/\r?\n$/, '');
}

/** API base URL. Only the web server calls the API; browsers never do (ADR 0009). */
export function serverApiBaseUrl(env: Env = process.env): string {
  return env.SIDETRACK_API_BASE_URL || 'http://localhost:8000';
}

/**
 * JSON headers carrying the web app's own token, for server-side API calls only.
 * `actingUserId` must come from the server session, never from a request.
 */
export function serverApiHeaders(
  env: Env = process.env,
  actingUserId?: string,
): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = readSecret('SIDETRACK_WEB_API_TOKEN', env);
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (actingUserId) headers[ACT_AS_HEADER] = `user:${actingUserId}`;
  return headers;
}
