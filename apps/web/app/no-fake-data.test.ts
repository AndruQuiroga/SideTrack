/**
 * Guard for spec web/data-honesty: the site never shows invented data.
 * Fails when source under app/ reintroduces fallback generators, demo users or random values.
 */
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { test } from 'node:test';

const APP_DIR = import.meta.dirname;

const BANNED: Array<[RegExp, string]> = [
  [/Math\.random/, 'random values'],
  [/WithFallback/, 'fallback fetcher'],
  [/source:\s*'fallback'|===\s*'fallback'/, 'fallback data marker'],
  [
    /\b(getDemo\w*|demoTracks|getSample\w*|createSample\w*|createFallback\w*)\b/,
    'demo/sample generator',
  ],
  [/\/u\/demo\b|user[AB]=demo|id:\s*'demo'|\(\s*'demo'\s*\)/, 'placeholder "demo" user'],
];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.(ts|tsx)$/.test(path) && !/\.test\.ts$/.test(path))
    .map((path) => join(dir, path));
}

test('app/ contains no fallback, demo or random data', () => {
  const violations: string[] = [];
  for (const file of sourceFiles(APP_DIR)) {
    const lines = readFileSync(file, 'utf8').split('\n');
    lines.forEach((line, index) => {
      for (const [pattern, label] of BANNED) {
        if (pattern.test(line)) {
          violations.push(`${relative(APP_DIR, file)}:${index + 1} ${label}: ${line.trim()}`);
        }
      }
    });
  }
  assert.deepEqual(violations, [], `Invented data found:\n${violations.join('\n')}`);
});
