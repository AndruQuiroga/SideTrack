import Link from 'next/link';
export function ClubTabs({ archive = false }: { archive?: boolean }) {
  return (
    <nav className="club-tabs" aria-label="Club">
      <Link href="/club/current" aria-current={!archive ? 'page' : undefined}>
        Latest scheduled week
      </Link>
      <Link href="/club" aria-current={archive ? 'page' : undefined}>
        Archive
      </Link>
    </nav>
  );
}
