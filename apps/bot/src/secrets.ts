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
