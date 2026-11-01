# Mockups: presenting the listening mirror

Text wireframes for the `add-*` analysis proposals. Every figure shown is a labelled
example, not data. Every view must follow `openspec/specs/web/data-honesty`: it renders only
stored values, shows the sample size, and has an explicit "not enough data" state.

## 1. Weekly card (Discord embed and web)

```
┌──────────────────────────────────────────────────────────────┐
│ Week of 20–26 Oct · 84 chosen plays (61 with audio, 73%)      │
│ 2 night-autoplay sessions left out                            │
├──────────────────────────────────────────────────────────────┤
│ Mood      ◀ darker than usual ▶   −1.3 σ   (52-week baseline) │
│ Energy    ≈ your usual             +0.2 σ                     │
│ Themes    ▇▇▇▇▇▇ sad slowed lo-fi 41%                         │
│           ▇▇▇ euphoric melodic bass 22%                       │
│           ▇▇ ambient sleep (autoplay, not counted)            │
│ Comfort   62% repeats · 3 new sounds far from your centre     │
│ Clock     late evenings (22–01) carried 55% of plays          │
├──────────────────────────────────────────────────────────────┤
│ How did this week feel?  😞 1  2  3  4  5 😊   ⚡ 1 2 3 4 5     │
└──────────────────────────────────────────────────────────────┘
```

- Reactions are the one-tap check-in; the bot records the user, week and value.
- Empty state: "Fewer than 20 chosen plays had audio this week, so there is no mood
  reading. 12 plays were from tracks with no audio yet."

## 2. Mood trail (web, `/listening/mirror`)

Scatter of one dot per week on valence (x) × arousal (y), connected in time, last 12 weeks
bold, older faded; a faint ellipse shows the 52-week baseline. Hover: week, n plays, top
theme. Because V and A correlate at ~0.9 on this library, the axes are labelled "darker ↔
brighter" and "calmer ↔ more intense" and the help text says the trail will tend to run
diagonally. Colour-blind-safe diverging palette; dark and light themes.

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
threshold are drawn as a gap, never interpolated.

## 4. Taste galaxy

2-D map (UMAP or PCA of the 512-d vectors, computed on the worker, stored per model
revision) of every embedded track; this week's plays highlighted; clusters hulled and
labelled. Mobile: pinch-zoom canvas, label density reduced. Hover/tap: artist – title,
plays, theme, mood percentile.

## 5. Listening clock

Hour × weekday heat grid, coloured by play count, with a toggle to colour by mood
percentile. Night-autoplay sessions are hatched. Uses the user's timezone; without one the
view says so and offers the settings link.

## 6. Track analysis card (`/tracks/{id}`)

```
Some Artist — Deep Cut                       audio: full track, confirmed
Sounds like: sad slowed lo-fi · 2nd: wave · (zero-shot, calibrated)
Mood   darker than 78% of your library · calmer than 64%
Tempo  70 BPM (or 140 half-time)   Key  F minor (low confidence)
Loud   −11.2 LUFS, range 6 dB   Bright  18th percentile   Bass  heavy (91st)
Vocals present (0.82)           Structure  drop at 1:02
Nearest in your library: … · … · …   "why": closest 10 s windows at 1:02 ↔ 0:58
Every value: tool and version on hover. Missing facets read "not computed".
```

## 7. Compatibility (`/compare/{a}/{b}`)

```
You × Member B — sound overlap 0.41 (moderate)   based on 612 and 388 embedded tracks
Mood   you sit darker/calmer; they sit brighter   (distance 0.9 σ)
Shared sound-worlds   melodic bass (both), lo-fi (you), liquid dnb (them)
Bridge songs   5 tracks near both of you → nominate
Translation    your "Artist X" ≈ their "Artist Y" (cosine 0.87)
```

Shown only after both users opted in; a member leaving deletes their side.

## 8. Check-in correlation view

"Over 23 weeks with a check-in, weeks with darker music were followed by lower mood
reports (ρ = −0.31, 95% interval −0.62 to +0.08). That's weak evidence; 29 more weeks
would narrow it." Below n = 8: "Not enough check-ins yet (3 of 8)."

## Anti-patterns (do not build)

Personality types; "you are sad"; placeholder sparklines; shares without n; interpolating
missing weeks; colouring by raw valence without the baseline; serving audio.
