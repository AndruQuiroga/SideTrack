'use client';

import { useState } from 'react';

type Props = {
  onChange?: (enabled: boolean) => void;
};

export default function SeasonToggle({ onChange }: Props) {
  const [enabled, setEnabled] = useState(false);

  return (
    <button
      type="button"
      className="text-sm underline"
      onClick={() => {
        const next = !enabled;
        setEnabled(next);
        onChange?.(next);
      }}
    >
      {enabled ? 'Season Replay: on' : 'Season Replay'}
    </button>
  );
}
