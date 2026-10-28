export function RatingBadge({ value, count }: { value?: number | null; count?: number }) {
  if (value == null)
    return (
      <span className="status-text">{count === 0 ? 'No ratings yet' : 'Rating unavailable'}</span>
    );
  return (
    <span className="rating">
      {value.toFixed(1)} / 5
      {typeof count === 'number' && (
        <small>
          {' '}
          · {count} {count === 1 ? 'rating' : 'ratings'}
        </small>
      )}
    </span>
  );
}
