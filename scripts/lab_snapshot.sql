-- Listening Lab snapshot: one row per play of one user. Read-only: a single SELECT.
--
--   psql -q --csv -v user_id=<user uuid> -f scripts/lab_snapshot.sql > lab-snapshot.csv
--
-- Write the CSV outside the repository; it is personal data. Columns:
--   played_at, artist, title, session_start, session_end, session_kind, sha256, doubtful_timing
-- session_kind is the effective kind: the user's review (keep, autoplay) if there is one, else the
-- rule's flag. sha256 is the preferred linked asset (full before preview), empty when none is
-- linked. doubtful_timing is true for a session of 20 or more listens at over 30 listens an hour.
WITH preferred AS (
    SELECT DISTINCT ON (l.track_id)
        l.track_id,
        a.sha256
    FROM track_audio_links AS l
    JOIN audio_assets AS a ON a.id = l.asset_id
    ORDER BY
        l.track_id,
        CASE CAST(a.kind AS text) WHEN 'full' THEN 0 ELSE 1 END,
        l.ambiguous,
        l.confidence DESC,
        l.linked_at,
        a.sha256
)
SELECT
    e.played_at AS played_at,
    t.artist_name AS artist,
    t.title AS title,
    s.started_at AS session_start,
    s.ended_at AS session_end,
    COALESCE(o.override, s.kind, 'unknown') AS session_kind,
    COALESCE(p.sha256, '') AS sha256,
    COALESCE(
        s.listen_count >= 20
        AND s.listen_count > 30 * EXTRACT(EPOCH FROM (s.ended_at - s.started_at)) / 3600.0,
        false
    ) AS doubtful_timing
FROM listen_events AS e
JOIN tracks AS t ON t.id = e.track_id
LEFT JOIN listen_sessions AS s ON s.id = e.session_id
LEFT JOIN listen_session_overrides AS o
    ON o.user_id = s.user_id AND o.started_at = s.started_at AND o.ended_at = s.ended_at
LEFT JOIN preferred AS p ON p.track_id = e.track_id
WHERE e.user_id = CAST(:'user_id' AS uuid)
ORDER BY e.played_at, t.artist_name, t.title;
