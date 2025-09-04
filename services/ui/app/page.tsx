import Link from 'next/link';

export default function Home() {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <h1>Welcome to SideTrack</h1>
      <p>A hosted mood/taste analytics pipeline for your music listening history.</p>
      <nav style={{ display: 'grid', gap: 8 }}>
        <Link href="/trajectory">Taste Trajectory</Link>
        <Link href="/moods">Moods</Link>
        <Link href="/radar">Weekly Radar</Link>
        <Link href="/outliers">Outliers</Link>
        <Link href="/settings">Settings</Link>
      </nav>
    </div>
  );
}

