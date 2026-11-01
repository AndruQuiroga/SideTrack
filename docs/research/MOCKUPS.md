# Mockups: presenting the listening mirror

Text wireframes for the `add-*` analysis proposals. Every figure shown is a labelled
example, not data. Every view must follow `openspec/specs/web/data-honesty`: it renders only
stored values, shows the sample size, and has an explicit "not enough data" state.
See the [research notes](MUSIC-ANALYSIS-RESEARCH-NOTES.md) for evidence, accessibility,
privacy and proposal follow-ups. Numeric minimums below are draft product choices, not
validated guarantees of statistical reliability.

## 1. Weekly card (Discord embed and web)

```
┌──────────────────────────────────────────────────────────────┐
│ Week of 20–26 Oct · 84 counted plays (61 analyzed, 73%)       │
│ 2 possible autoplay sessions excluded  [Review]              │
├──────────────────────────────────────────────────────────────┤
│ Music character estimate: darker than usual  −1.3 σ           │
│ Arousal estimate: around your usual           +0.2 σ          │
│ Themes (% of 61 eligible plays; suggested labels)            │
│           ▇▇▇▇▇▇ sad slowed lo-fi 41%                         │
│           ▇▇▇ euphoric melodic bass 21%                       │
│ Comfort   62% repeats · 3 new sounds far from your centre     │
│ Clock     late evenings (22–01) carried 55% of plays          │
├──────────────────────────────────────────────────────────────┤
│ Optional private check-in  [Open privately]                  │
└──────────────────────────────────────────────────────────────┘
```

- The 52-week baseline, theme denominator and meaning of “repeat” are
  disclosed. The illustration assumes all 61 analyzed plays have current mood and theme
  results; actual denominators can differ. Autoplay is a reviewable suggestion, not
  proof of intent. Changing a session classification updates the counts.
- Check-ins are opt-in, private and deletable. Use a private interaction such as a DM
  or private web form, not visible reactions on a shared club message.
- Empty state: "Fewer than 20 counted plays had usable mood analysis this week, so
  there is no mood reading. 12 plays were from tracks with no audio yet."

## 2. Mood trail (web, `/listening/mirror`)

Scatter of one dot per week on estimated music valence (x) × arousal (y), with the trail
broken at missing weeks; a faint ellipse shows an available 52-week baseline. Hover or
focus: week, eligible plays, coverage and top theme. Label the axes "darker ↔ brighter"
and "calmer ↔ more intense"; distinguish perceived music character from felt mood.
The experimental probe's axes are highly correlated on the owner's library, but do not
assume that number for every user or probe. Provide a keyboard-accessible data table and
use shapes and text as well as color.

```
 intense ▲            ○ wk38
         │        ○ wk41  ●wk43
         │    ○ wk40 ● wk44
         │ ○ wk39      ●wk42
  calm   └──────────────────────▶
        darker              brighter
```

## 3. Theme river

Streamgraph of play-weighted theme shares per week; bands named by the cluster's top terms,
renamable. Clicking a band lists the week's tracks in it. Weeks under the minimum-plays
threshold are drawn as a gap, never interpolated. Show the classified-play denominator
and an accessible table; labels are suggestions rather than definitive genre claims.

## 4. Taste galaxy

2-D map (UMAP or PCA of the 512-d vectors, computed on the worker, stored with its
model, pipeline, corpus and projection versions) of every embedded track; this week's
plays highlighted; clusters hulled and labelled. Mobile: pinch-zoom canvas, label
density reduced. Hover/tap: artist – title, plays, theme, mood percentile. Explain that
projection can distort neighbourhoods and does not prove clusters: calculate actual
nearest tracks in the original vector space. Provide an accessible searchable list, not
a canvas-only interface.

## 5. Listening clock

Hour × weekday heat grid, coloured by play count, with a toggle to colour by mood
percentile. Possible autoplay sessions are hatched and reviewable; hatching, labels and
a table carry information without color alone. Uses the user's timezone; without one
the view says so and offers the settings link.

## 6. Track analysis card (`/tracks/{id}`)

```
Some Artist — Deep Cut               full asset, user-confirmed link
Analyzed 03:00 of 05:12
Suggested sounds: sad slowed lo-fi · wave  (model estimates)
Music character: darker than 78% of your eligible library · calmer than 64%
Tempo: 70 or 140 BPM (half/double-time ambiguity)  Key: F minor (uncertain)
Loudness: −11.2 LUFS, range 6 dB   Brightness: 18th percentile
Bass: 91st percentile   Vocals: possibly present
Structure: candidate boundary at 1:02   [Show method]
Nearest in your library: [track A] · [track B] · [track C]
Every value: source, analyzed duration, tool and version on focus.
```

“Not computed,” “no audio,” “uncertain link,” “stale” and “analysis failed” are
different states. The mockup is not a claim that these facets are implemented. A
section-to-section “why” needs newly stored timestamped representations and validation;
the existing pooled vector cannot produce it.

## 7. Compatibility (`/compare/{a}/{b}`)

```
You × Member B — exploratory sound comparison
Coverage: 612 of your 800 tracks · 388 of their 520 tracks have eligible audio
Shared sound-worlds: melodic bass (both)
Distinct examples: lo-fi (you) · liquid dnb (them)
Bridge candidates: 5 tracks near both libraries → review and nominate
Method: model and weighting details  [Learn more]
```

Shown only after both users opt in. Withdrawing consent removes their side and derived
comparison data according to the sharing and deletion policy. Do not assign
unvalidated “low/moderate/high” labels or imply a verdict on either person.

## 8. Check-in correlation view

"In this example, 23 weeks have both measures. Higher music valence and higher
self-reported mood occurred together (ρ = +0.31; 95% interval −0.08 to +0.62). The
interval includes zero; this does not establish a cause." Below the draft n = 8 product
threshold: "Not enough check-ins yet (3 of 8)." Eight observations do not make a
correlation reliable, and more weeks do not guarantee a narrower interval. Only show an
interval when the chosen method accounts appropriately for the data's dependence and
other limitations.

## 9. Audio-first library search

```
Search your analyzed library
[ melodic bass with airy vocals                       ] [Search]
Include: [x] full tracks  [x] previews     [Model and limitations]
450 of 800 tracks have eligible embeddings for this search.

1. Some Artist — Deep Cut       full · first 03:00 analyzed
2. Another Artist — Track B      preview · 00:30 analyzed
3. Third Artist — Track C        full · first 03:00 analyzed
[Mark useful] [Not relevant] [Show how this list was ranked]
```

The explanation identifies the text/audio model, revision and comparison method, not a
made-up reason or probability. A prompt change can reorder results. “No matching
results,” “no eligible audio” and “analysis failed” are separate states; feedback is
private and optional.

## 10. Coverage and listening controls

```
Week of 20–26 Oct · 84 counted plays
45   plays with full assets and usable analysis
16   plays with preview-only assets and usable analysis
 9   plays with linked audio but no required current analysis
14   plays without a confident audio link
     2 possible autoplay sessions excluded  [Review sessions]

Analysis: MuQ-MuLan · model revision and pipeline [Details]
Missing: [Review links] [See unprocessed audio]
Check-ins: private · optional  [Export] [Delete my check-ins]
```

The four play counts sum to 84 in this example. Actual coverage must be computed for
the selected facet: an embedding, a mood score and a theme label can each have a
different denominator. Link corrections and session classifications are user-reviewable;
no action here schedules yt-dlp or serves audio.

## 11. Sound-world explorer

```
Your sound-worlds · 61 eligible plays this week

Suggested: sad slowed lo-fi   25 plays (41%)
Representative tracks: [track A] · [track B] · [track C]
[Rename for me] [This label is wrong] [Review tracks]

Suggested: euphoric melodic bass   13 plays (21%)
Other or uncertain: 23 plays (38%)
[Show label method and model] [Compare another week]
```

Names and memberships are suggestions, not facts about genre or the listener. Keep
unclassified tracks visible and preserve the user's names or corrections when possible
across model and clustering changes.

## 12. Listening journey

```
Your listening over time
2019–2026 · history imported through [date] · [Coverage details]

[2019] ───── [2021] ─── gap ─── [2024] ───── [2026]
  2019: most-played tracks [View]
  2024: an estimated change in your analyzed listening [Review tracks]
  2026: tracks played again after a long break [View]

Compare periods  [Earlier] [Later]
```

Gaps denote missing or insufficient history, not silence. A detected shift is a
candidate for exploration, not a personal event or a claim that the music caused one.

## 13. Share preview and consent

```
Share a listening card
[x] top tracks and period     [x] sample size and analysis coverage
[ ] listening clock           [ ] theme estimates
[ ] private check-in          [ ] another member's data

[Preview exactly what will be shared]
[Share]  [Cancel]
```

Nothing is shared until explicitly requested. Another member's data needs their
separate consent; private check-ins are excluded by default. Explain the destination,
what can be revoked, and any limits on retracting an already exported image.

## 14. Build a sound bridge

```
From [starting track] to [ending track]
Sound: [closer ─────────●──── exploratory]     [Generate candidates]

1. Starting track                   chosen by you
2. Candidate bridge track           [Replace] [Not relevant]
3. Another candidate                [Replace] [Not relevant]
4. Ending track                     chosen by you

Based on eligible audio embeddings · [Coverage and ranking method]
[Save the track list] [Start over]
```

Listeners can review and reorder the proposed metadata-only list. A smooth path in an
embedding space is not necessarily a good DJ transition; do not promise beatmatching or
serve audio. Prompt for missing endpoints or insufficient analyzed candidates instead
of filling the list with placeholders.

## Anti-patterns (do not build)

Personality types; "you are sad"; placeholder sparklines; shares without n; interpolating
missing weeks; color-only charts; implying autoplay is known intent; presenting audio
similarity as recording identity; serving audio.
