export default function WeekDetailLoading() {
  return (
    <div className="space-y-4">
      <div className="card animate-pulse space-y-3">
        <div className="h-4 w-32 rounded bg-slate-800" />
        <div className="h-6 w-1/2 rounded bg-slate-800" />
        <div className="h-3 w-1/3 rounded bg-slate-800" />
      </div>
      <div className="card animate-pulse space-y-2">
        <div className="h-4 w-24 rounded bg-slate-800" />
        <div className="h-3 w-full rounded bg-slate-800" />
        <div className="h-3 w-5/6 rounded bg-slate-800" />
      </div>
    </div>
  );
}
