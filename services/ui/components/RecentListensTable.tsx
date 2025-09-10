'use client';

import { useState } from 'react';
import { useRecentListens } from '../lib/query';
import { Button } from './ui/button';

const fmt = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'short',
  timeStyle: 'short',
});

type Props = {
  pageSize?: number;
};

export default function RecentListensTable({ pageSize = 10 }: Props) {
  const { data, isLoading, error } = useRecentListens(50);
  const [page, setPage] = useState(0);

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading...</div>;
  }
  if (error) {
    return <div className="text-sm text-red-500">Failed to load listens</div>;
  }

  const listens = data?.listens ?? [];
  const pageCount = Math.max(1, Math.ceil(listens.length / pageSize));
  const start = page * pageSize;
  const current = listens.slice(start, start + pageSize);

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="hidden min-w-full text-sm sm:table">
          <thead>
            <tr className="text-left">
              <th className="px-2 py-1 font-medium">Title</th>
              <th className="px-2 py-1 font-medium">Artist</th>
              <th className="px-2 py-1 font-medium">Played</th>
            </tr>
          </thead>
          <tbody>
            {current.map((ls) => (
              <tr
                key={`${ls.track_id}-${ls.played_at}`}
                tabIndex={0}
                className="focus:bg-white/5"
              >
                <td className="px-2 py-1 font-medium">{ls.title}</td>
                <td className="px-2 py-1 text-muted-foreground">
                  {ls.artist ?? '\u00A0'}
                </td>
                <td className="px-2 py-1 whitespace-nowrap text-muted-foreground">
                  {fmt.format(new Date(ls.played_at))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul className="divide-y divide-border sm:hidden">
          {current.map((ls) => (
            <li key={`${ls.track_id}-${ls.played_at}`} className="py-2">
              <div className="font-medium">{ls.title}</div>
              {ls.artist && (
                <div className="text-xs text-muted-foreground">{ls.artist}</div>
              )}
              <div className="text-xs text-muted-foreground">
                {fmt.format(new Date(ls.played_at))}
              </div>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
        >
          Previous
        </Button>
        <span className="text-xs text-muted-foreground">
          Page {page + 1} of {pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          disabled={page >= pageCount - 1}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

