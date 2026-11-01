import type { Rediscovery, RediscoveryDismissal } from '@sidetrack/api-client';
import type { Access } from '../lib/server-api';
import { formatUtc } from '../lib/club';
import { describePeak, rediscoveryHref } from '../lib/rediscovery';
import { PageShell } from './page-shell';
import { AccessNotice, Unavailable } from './ui';

const ACTION = '/api/rediscovery';

function Hidden({
  action,
  autoplay,
  trackId,
}: {
  action: string;
  autoplay: boolean;
  trackId?: string;
}) {
  return (
    <>
      <input type="hidden" name="action" value={action} />
      <input type="hidden" name="autoplay" value={autoplay ? '1' : '0'} />
      {trackId && <input type="hidden" name="track_id" value={trackId} />}
    </>
  );
}

function Rules({ data }: { data: Rediscovery }) {
  const { rules } = data;
  return (
    <section className="section" aria-labelledby="rules-heading">
      <h2 id="rules-heading">How this list is made</h2>
      <p className="small muted">
        A track is listed when it was played at least {rules.min_plays} times within{' '}
        {rules.window_days} days and has not been played for {rules.forgotten_days} days. This is a
        play-count rule on your imported history (rule {rules.rule_version}), not a record of what
        you enjoyed.
      </p>
      <ul className="small muted">
        {data.coverage_start && data.coverage_end && (
          <li>
            Imported history covers {formatUtc(data.coverage_start)} to{' '}
            {formatUtc(data.coverage_end)}.
          </li>
        )}
        <li>
          {data.include_autoplay
            ? 'Plays from sessions marked as autoplay are included.'
            : `${data.excluded_autoplay_plays} plays from sessions marked as autoplay were left out.`}
        </li>
        <li>
          {data.unknown_session_plays} plays came from sessions that could not be classified because
          no timezone applies; they are included.
        </li>
        {data.dismissed_hidden > 0 && <li>{data.dismissed_hidden} dismissed tracks are hidden.</li>}
        <li>
          Different versions or uploads of the same song may be counted separately, so a track’s
          plays can be split.
        </li>
      </ul>
      <div className="actions">
        <a
          className="button"
          href={rediscoveryHref(!data.include_autoplay)}
          aria-label={
            data.include_autoplay ? 'Leave out autoplay sessions' : 'Include autoplay sessions'
          }
        >
          {data.include_autoplay ? 'Leave out autoplay sessions' : 'Include autoplay sessions'}
        </a>
      </div>
    </section>
  );
}

function StateMessage({ data }: { data: Rediscovery }) {
  switch (data.state) {
    case 'not_imported':
      return (
        <section className="access-state">
          <h2>No listening history has been imported</h2>
          <p>
            Nothing can be called forgotten without imported history. This is not the same as having
            no listens.
          </p>
        </section>
      );
    case 'coverage_gap':
      return (
        <section className="access-state">
          <h2>Your imported history stops too early</h2>
          <p>
            It ends {data.coverage_end ? formatUtc(data.coverage_end) : 'before now'}, so recent
            listening is missing and nothing can be called forgotten yet.
          </p>
        </section>
      );
    case 'insufficient_history':
      return (
        <section className="access-state">
          <h2>Not enough recent listening to judge</h2>
          <p>
            The last {data.rules.forgotten_days} days hold {data.recent_plays ?? 0} plays on{' '}
            {data.recent_days ?? 0} days; at least {data.rules.min_recent_plays} plays on{' '}
            {data.rules.min_recent_days} days are needed.
          </p>
        </section>
      );
    case 'none_found':
      return (
        <section className="access-state">
          <h2>Nothing matches</h2>
          <p>
            No track was played at least {data.rules.min_plays} times within{' '}
            {data.rules.window_days} days and then left alone for {data.rules.forgotten_days} days.
          </p>
        </section>
      );
    default:
      return null;
  }
}

function Tracks({ data }: { data: Rediscovery }) {
  if (!data.tracks.length) return null;
  return (
    <section className="section" aria-labelledby="tracks-heading">
      <h2 id="tracks-heading">Played a lot, not lately</h2>
      {data.tracks.map((track) => (
        <div className="data-row" key={track.track_id}>
          <span className="row-mark" aria-hidden="true">
            ♪
          </span>
          <p>
            <strong>{track.title}</strong>
            <span className="small muted">{track.artist_name}</span>
            <span className="small muted">
              {describePeak(track)}: {track.peak_plays} plays within {data.rules.window_days} days ·
              last played {formatUtc(track.last_played_at)} · {track.total_plays} plays in total
            </span>
          </p>
          <form method="post" action={ACTION} className="actions">
            <Hidden action="dismiss" autoplay={data.include_autoplay} trackId={track.track_id} />
            <button className="text-button" type="submit" name="reason" value="not_now">
              Not now
            </button>
            <button className="text-button" type="submit" name="reason" value="not_a_favourite">
              Not a favourite
            </button>
          </form>
        </div>
      ))}
    </section>
  );
}

function Dismissed({
  result,
  autoplay,
}: {
  result: Access<RediscoveryDismissal[]>;
  autoplay: boolean;
}) {
  if (result.state === 'unavailable') return <Unavailable what="dismissed tracks" />;
  if (result.state !== 'ok' || !result.data.length) return null;
  return (
    <section className="section" aria-labelledby="dismissed-heading">
      <h2 id="dismissed-heading">Dismissed</h2>
      {result.data.map((row) => (
        <div className="data-row" key={row.track_id}>
          <span className="row-mark" aria-hidden="true">
            ♪
          </span>
          <p>
            <strong>{row.title ?? 'Track removed'}</strong>
            <span className="small muted">
              {row.artist_name ? `${row.artist_name} · ` : ''}
              {row.reason === 'not_now' ? 'Not now' : 'Not a favourite'}
            </span>
          </p>
          <form method="post" action={ACTION}>
            <Hidden action="restore" autoplay={autoplay} trackId={row.track_id} />
            <button className="text-button" type="submit">
              Restore
            </button>
          </form>
        </div>
      ))}
      <form method="post" action={ACTION} className="actions">
        <Hidden action="restore_all" autoplay={autoplay} />
        <button className="button" type="submit">
          Restore all
        </button>
      </form>
    </section>
  );
}

export function RediscoveryPage({
  result,
  dismissals,
  autoplay,
}: {
  result: Access<Rediscovery>;
  dismissals: Access<RediscoveryDismissal[]>;
  autoplay: boolean;
}) {
  return (
    <PageShell
      title="Played a lot, not lately"
      description="Tracks you played often in one stretch of your imported history and have not played for a year. Only you can see this page."
      accent="Listening"
    >
      {result.state !== 'ok' ? (
        <AccessNotice
          state={result.state === 'not-found' ? 'forbidden' : result.state}
          what="rediscovery list"
          audience="its owner"
          returnTo={rediscoveryHref(autoplay)}
        />
      ) : (
        <>
          <StateMessage data={result.data} />
          <Tracks data={result.data} />
          {result.data.state !== 'not_imported' && <Rules data={result.data} />}
          <Dismissed result={dismissals} autoplay={autoplay} />
        </>
      )}
    </PageShell>
  );
}
