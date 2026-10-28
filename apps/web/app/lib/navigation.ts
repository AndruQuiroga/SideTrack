export const navigationItems = [
  { href: '/', label: 'Overview', symbol: '⌂' },
  { href: '/club/current', label: 'Club', symbol: '◎' },
  { href: '/listening', label: 'Listening', symbol: '≡' },
  { href: '/settings', label: 'Account', symbol: '○' },
] as const;

export function isNavigationActive(href: string, path: string): boolean {
  if (href === '/club/current') return path.startsWith('/club');
  if (href === '/listening') return path === href || /^\/u\/[^/]+\/listening$/.test(path);
  return path === href;
}

/** Untrusted navigation values never become cross-origin OAuth return URLs. */
export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string' || value.length > 2048) return '/';
  try {
    let decoded = value;
    for (let i = 0; i < 3; i++) {
      if (!decoded.startsWith('/') || decoded.startsWith('//') || unsafeCharacters(decoded))
        return '/';
      const next = decodeURIComponent(decoded);
      if (next === decoded) break;
      decoded = next;
    }
    if (!decoded.startsWith('/') || decoded.startsWith('//') || unsafeCharacters(decoded))
      return '/';
    const parsed = new URL(value, 'https://sidetrack.invalid');
    return parsed.origin === 'https://sidetrack.invalid'
      ? parsed.pathname + parsed.search + parsed.hash
      : '/';
  } catch {
    return '/';
  }
}
function unsafeCharacters(value: string): boolean {
  return (
    value.includes('\\') ||
    [...value].some((char) => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)
  );
}
export function signInHref(returnTo: string): string {
  return `/login?from=${encodeURIComponent(safeReturnPath(returnTo))}`;
}
