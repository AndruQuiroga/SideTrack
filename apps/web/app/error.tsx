'use client';

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorProps) {
  return (
    <html lang="en">
      <body className="bg-sidetrack-bg text-slate-50">
        <main className="mx-auto max-w-3xl px-4 py-12">
          <div className="space-y-3 rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-soft">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Something went wrong</p>
            <h2 className="text-2xl font-semibold text-white">We hit a snag</h2>
            <p className="text-sm text-slate-300">{error.message || 'An unexpected error occurred.'}</p>
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={() => reset()}
                className="rounded-full bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-emerald-400"
              >
                Try again
              </button>
              <a
                href="/club"
                className="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-emerald-400 hover:text-white"
              >
                Back to archive
              </a>
            </div>
          </div>
        </main>
      </body>
    </html>
  );
}
