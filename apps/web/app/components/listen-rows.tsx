import type { RecentListen } from '@sidetrack/api-client';

export function ListenRows({ listens }: { listens: RecentListen[] }) {
  return (
    <div>
      {listens.map((listen, index) => (
        <div className="data-row" key={`${listen.listened_at}-${index}`}>
          <span className="row-mark" aria-hidden="true">
            ♪
          </span>
          <p>
            <strong>{listen.track_name}</strong>
            <span className="small muted">
              {listen.artist_name}
              {listen.source && ` · ${listen.source}`}
            </span>
          </p>
          <time className="small muted numeric" dateTime={listen.listened_at}>
            {new Intl.DateTimeFormat('en-US', {
              timeZone: 'UTC',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            }).format(new Date(listen.listened_at))}
          </time>
        </div>
      ))}
    </div>
  );
}
