# Product vision: the listening mirror

This is a direction document, not a claim that anything works. `docs/STATUS.md` holds
what works today, and each feature here still needs its own OpenSpec change.

## The goal

The question Sidetrack's audio work exists to answer is: **week by week, can my
listening history reveal my mood and the musical themes I'm drawn to without noticing?**

Around that question:
- visuals that describe the owner's taste and recent listening
- a music compatibility test between people

This rules out a lot. Sidetrack isn't a streaming service or a general recommender, and
it never serves audio (ADR 0007). It reads what was played, analyses the sound, and
reflects it back.

### Why audio-first

- **Metadata covers little of this music.** In the first benchmark, roughly half of the
  owner's tracks were unknown to AcoustID. Uploads arrive through channels
  (AirwaveMusicTV, MrSuicideSheep), slowed edits and autoplay.
- **Spotify has nothing to add.** It is metadata-only for this app, so its audio
  features and recommendations aren't available.
- **Sidetrack has what nothing else does:** the actual audio, and the owner's full
  ListenBrainz history (74,826 listens, 2019–2026).

## 1. Weekly listening profile

Each week becomes a profile computed from the tracks played. Each track's audio
contribution is weighted by its plays.

| Signal | Captures | Source |
| --- | --- | --- |
| Mood | valence (dark↔bright), arousal (calm↔intense) | a mood probe on the chosen audio embedding (section 5) |
| Themes | recurring sound-worlds, e.g. "sad slowed lo-fi", "euphoric melodic bass" | clusters in the embedding space, named with a text tower (MuQ-MuLan) or tag models |
| Lyric themes | heartbreak, nostalgia, escape, self-worth | optional: vocal separation and transcription, then topics; heavy, batch only |
| Comfort against exploring | replaying favourites, or seeking new sounds | repeat rate, and distance from the long-term taste centroid |
| Context | late nights, sleep sessions, bursts | session analysis (`audio-lab seeds` already detects night sessions) |

**Chosen plays only.** Autoplay and sleep-tab sessions reflect the service's choices, not
the listener's state. They are tracked separately or down-weighted, never mixed in.

**Baseline.** Seven years of history define "normal you". Each week is described
against that baseline ("darker than usual"), never in absolute terms.

## 2. Prediction needs an answer key

Music describes; it doesn't by itself prove a mood. To test whether listening predicts
mood, Sidetrack needs self-reports.
- **Weekly check-in:** a one-tap Discord or web check-in, "this week felt" 1–5, plus
  energy 1–5. It's optional, and the analysis says how many check-ins it rests on.
- **Questions it can then answer:**
  - Does listening valence follow the check-in, or run ahead of it?
  - Do certain themes appear before good or hard stretches?
  - Does last week's listening predict this week's check-in better than a baseline
    (last week's check-in, or the average)?

**Honesty rule:** a correlation is shown with its sample size and a plain-language
uncertainty. The product never says "you are sad". It says "your music was darker than
usual, and in past weeks like this you reported …".

## 3. Visuals

- **Mood trail:** one dot per week on the valence × arousal plane, connected in time.
- **Theme river:** a streamgraph of sound-themes by week, where eras show as bands.
- **Taste galaxy:** a 2D map of the whole library by sound, with this week's plays
  highlighted.
- **Listening clock:** hour × weekday, coloured by mood.
- **Weekly card:** a short Discord post with the week's mood shift, its dominant theme
  and its new sounds.

The visuals follow `openspec/specs/web/data-honesty`: no chart is drawn from placeholder data.

## 4. Compatibility test

Compare how close two people's music sounds, not how many artists they share. Two people
with no artists in common can still live in the same sound.
- **Overlap:** how much the two taste distributions overlap in the embedding space.
- **Mood match:** whether they occupy the same valence and arousal region.
- **Bridge songs:** tracks near both distributions, which make good album-club
  nominations.
- **Translation:** for an artist one person loves, the closest-sounding artist in the
  other's library.

Club members can take part through a public ListenBrainz username. Their history is
analysed only after they opt in, and it is deleted when they leave (`identity` deletion
already cascades).

## 5. Choosing the model for this goal

The duel benchmark (`docs/AUDIO-BENCHMARK.md`) narrowed the field to MuQ and MuQ-MuLan.
For this goal, the deciding test is **mood prediction**:
- **The test:** train a linear valence and arousal probe on each model's embeddings,
  using a public music-emotion dataset with per-track human ratings (candidates: DEAM,
  PMEmo; licences to check), and compare their cross-validated R².
- **The trade-off:** MuQ is best at recognising a recording (preview→full recall 0.96),
  while MuQ-MuLan groups genre and themes better and has a text tower for naming them.
- **Storing both is cheap:** about 1.5 KB per track per model.
- **Likely outcome:** MuQ handles identity, such as merging uploads, while the mood
  winner drives profiles.

## Order of work

Each step below is its own OpenSpec change.

1. **Finish the v2 finalist duels** (`add-audio-benchmark-v2`).
2. **Mood probe benchmark:** add the valence and arousal probe to the audio lab, and pick
   the model on mood R² together with the duels.
3. **Integration:** embeddings in pgvector on the `gpu` queue, and a GTX 1070 Ti
   environment (ADR 0004 follow-ups).
4. **Upload merging:** link the uploads of one recording, so plays and stats are honest.
5. **Weekly profile and check-in:** mood, themes, comfort against exploring, and
   context, plus the self-report.
6. **Visuals:** the mood trail and weekly card first, then the theme river, the taste
   galaxy and the listening clock.
7. **Compatibility:** opt-in for club members through ListenBrainz.
8. **Later, optional:** lyric themes, mood-mode queues as YT Music playlists, and
   new-release discovery from previews.

## Open questions

- **Check-in surface:** Discord, the web, or both. The owner decides.
- **Lyric transcription:** whether its value justifies GPU time on the 1070 Ti.
- **Period:** whether "week" means calendar weeks or rolling seven-day windows. Both are
  cheap; the visuals decide.
