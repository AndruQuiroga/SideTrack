interface RatingBadgeProps {
  value?: number | null;
  count?: number;
}

export function RatingBadge({ value, count }: RatingBadgeProps) {
  if (value === undefined || value === null) {
    return <span className="rounded-full bg-slate-900/70 px-3 py-1 text-[0.7rem] font-semibold text-slate-300">No ratings yet</span>;
  }

  const rounded = Math.round(value * 10) / 10;
  const fullStars = Math.floor(rounded);
  const halfStar = rounded - fullStars >= 0.5;

  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-3 py-1 text-[0.75rem] font-semibold text-amber-300 shadow-soft">
      <span>{rounded.toFixed(1)}</span>
      <span className="inline-flex text-[0.65rem] text-amber-300">
        {'★'.repeat(fullStars)}
        {halfStar && '½'}
      </span>
      {typeof count === 'number' && (
        <span className="ml-1 text-[0.65rem] font-medium text-slate-400">({count})</span>
      )}
    </div>
  );
}
