import Link from 'next/link';
export function ClubTabs({
  archive = false,
  singles = false,
}: {
  archive?: boolean;
  singles?: boolean;
}) {
  return (
    <nav className="club-tabs" aria-label="Club">
      <Link href="/club/current" aria-current={!archive && !singles ? 'page' : undefined}>
        Latest scheduled week
      </Link>
      <Link href="/club" aria-current={archive && !singles ? 'page' : undefined}>
        Archive
      </Link>
      <Link href="/club/singles" aria-current={singles ? 'page' : undefined}>
        Singles Night
      </Link>
    </nav>
  );
}
