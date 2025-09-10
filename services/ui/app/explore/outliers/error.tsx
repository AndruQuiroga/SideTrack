'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <p className="text-sm text-rose-400">Something went wrong.</p>
      <button onClick={() => reset()} className="rounded bg-emerald-500 px-4 py-2 text-white">
        Try again
      </button>
      <Link href="/" className="text-sm text-emerald-400 hover:underline">
        Go home
      </Link>
    </div>
  );
}
