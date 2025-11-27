type RatingBadgeProps = {
  value: number;
};

export function RatingBadge({ value }: RatingBadgeProps) {
  const rounded = Math.round(value * 2) / 2;
  const fullStars = Math.floor(rounded);
  const halfStar = rounded - fullStars >= 0.5;

  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-slate-900/70 px-2.5 py-1 text-[0.7rem] font-medium text-amber-300">
      <span>{rounded.toFixed(1)}</span>
      <span className="inline-flex text-[0.65rem] text-amber-300">
        {"★".repeat(fullStars)}
        {halfStar && "½"}
      </span>
    </div>
  );
}
