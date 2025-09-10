'use client';

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-4 p-4">
      <p className="text-sm text-rose-400">Failed to load insights: {error.message}</p>
      <button onClick={reset} className="rounded bg-emerald-500 px-4 py-2 text-sm text-emerald-950">
        Try again
      </button>
    </div>
  );
}
