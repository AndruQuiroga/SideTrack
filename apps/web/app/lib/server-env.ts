/**
 * Server-only configuration. Never import this from a client component: it reads files
 * and returns the API service token.
 */
import { readFileSync } from 'node:fs';

type Env = Record<string, string | undefined>;

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

/** API base URL for server-side calls: the internal address when one is configured. */
export function serverApiBaseUrl(env: Env = process.env): string {
  return env.SIDETRACK_API_BASE_URL || env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
}

/** JSON headers carrying the service token, for server-side API calls only. */
export function serverApiHeaders(env: Env = process.env): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = readSecret('SIDETRACK_API_TOKEN', env);
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}
