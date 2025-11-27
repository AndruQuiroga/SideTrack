export default function ClubLoading() {
  return (
    <div className="mx-auto max-w-6xl space-y-4 px-4 py-10">
      <div className="h-6 w-56 animate-pulse rounded-full bg-slate-800/70" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, idx) => (
          <div key={idx} className="card animate-pulse space-y-3 bg-slate-900/60">
            <div className="h-4 w-1/2 rounded bg-slate-800/80" />
            <div className="h-5 w-2/3 rounded bg-slate-800/80" />
            <div className="h-3 w-1/3 rounded bg-slate-800/80" />
          </div>
        ))}
      </div>
    </div>
  );
}
