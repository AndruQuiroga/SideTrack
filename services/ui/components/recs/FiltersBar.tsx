'use client';

interface Filters {
  newOnly: boolean;
  freshness: number;
  diversity: number;
  energy: number;
}

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
}

export default function FiltersBar({ filters, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={filters.newOnly}
          onChange={() => onChange({ ...filters, newOnly: !filters.newOnly })}
        />
        New artists only
      </label>
      <label className="flex items-center gap-2">
        Min freshness
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={filters.freshness}
          onChange={(e) =>
            onChange({ ...filters, freshness: parseFloat(e.target.value) })
          }
        />
      </label>
      <label className="flex items-center gap-2">
        Diversity
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={filters.diversity}
          onChange={(e) =>
            onChange({ ...filters, diversity: parseFloat(e.target.value) })
          }
        />
      </label>
      <label className="flex items-center gap-2">
        Energy
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={filters.energy}
          onChange={(e) =>
            onChange({ ...filters, energy: parseFloat(e.target.value) })
          }
        />
      </label>
    </div>
  );
}
