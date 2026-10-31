# SideTrack UX/UI research and design brief

Research date: 2026-10-28. Status: planning evidence and recommendations; not implementation or completed usability testing.

## Brief and method

The owner wants a full rework and specifically dislikes a bubbly, AI-generated feel. The review combined live desktop browser inspection, repository/specification audit, and primary-source design research. Recommendations below are inferences from that evidence, not universal design laws or measured user preferences.

Observed live: `https://sidetrack.network/`, `/discover`, and `/club` signed-out. Reviewed GuessSenpai at `https://guesssenpai.mustache.network/`. Rift at `https://rift.mustache.network/` settled behind an invite-only gate, so only the public entrance was visually assessed. Authenticated member data, mobile live workflows, and successful production OAuth were not inspected. `sidetrack.mustache.network` timed out; deployment configuration identified `sidetrack.network` as the actual public hostname. Discogs and the public mustache.network root could not be retrieved; no findings are attributed to their unobserved layouts.

## Observed problems and implications

| Observation | Evidence | Design implication |
| --- | --- | --- |
| Repeated large radii, pills, tinted surfaces and glows | `apps/web/app/globals.css`, `components/ui.tsx`, `components/page-shell.tsx`, live homepage | Replace decorative repetition with hierarchy tailored to content |
| Marketing language dominates the homepage | `apps/web/app/page.tsx`, live homepage | Signed-in overview should lead with club context and available listens |
| Discover promises personalized recommendations while status marks the capability stubbed | `apps/web/app/discover/page.tsx`, `docs/STATUS.md`, live Discover | Navigation should reflect usable capabilities |
| Settings promises Spotify now-playing/taste metrics | `apps/web/app/settings/page.tsx`, ADR 0003 | Describe actual integrations and remove unsupported connect promises |
| First nomination treated as winner and pitch parsed into album identity | `components/week-detail.tsx`, `components/club-gallery.tsx` | Resolve catalog metadata through stored winner ID |
| Latest-winner feature uses filtered sorted first entry | `components/club-gallery.tsx` | Separate featured chronological context from result ordering |
| Generated presence and histogram fallbacks | `components/club-gallery.tsx:35`, `components/week-detail.tsx:27` | Separate bug change against `web/data-honesty`; retain regression evidence |
| Listening log already uses a supported endpoint, unlike profile overview | `app/u/[id]/listening/page.tsx`, `app/lib/api/profile.ts`, status | Give listening an independent entry |
| OAuth control returns to root regardless of original page | `components/oauth-buttons.tsx` | Normalize and preserve same-origin destination |

The visual criticism is not a complaint against all rounded shapes or all cards. GuessSenpai uses cards effectively because each is a recognizable game destination. SideTrack's repeated containers often hold static explanations or repeated metadata with equal visual weight.

## Reference-site observations

### GuessSenpai

Observed: neutral charcoal canvas, quiet persistent sidebar, limited coral accent, direct Today heading, identifiable game thumbnails, visible daily state, underlined supporting links. Transfer the steady navigation and immediate access to meaningful activities. Do not transfer game-specific scoring or manufacture equivalent listening metrics.

### Rift

Observed public entrance: near-black canvas, concentrated lime identity, condensed display heading, concise explanation, one clear account action. Transfer the intentional typography and proportion. The authenticated exchange layout and workflow were not evaluated after the invite gate appeared.

### Cultural references

Bandcamp foregrounds music, editorial context, genres and scenes. Letterboxd foregrounds artwork, ratings, reviews, and lists. Their usefulness here is subject-centered content hierarchy; SideTrack does not need marketplace transactions, public social scale, carousels, or playback infrastructure.

Sources: [Bandcamp](https://bandcamp.com/), [Letterboxd](https://letterboxd.com/). Live desktop screenshots were inspected; incomplete media loading means this is not a full production visual audit of either service.

## Research findings and application

### Quiet application controls

Linear's 2024 redesign discusses alignment, visual noise, and navigation density. Its March 2026 refresh further reduces supporting navigation prominence and unnecessary icon treatment while making action placement predictable. Application: stable shell, quieter inactive navigation, consistent local page actions. Borrow those principles without reproducing Linear's branding or its product-specific density.

Sources: [Linear 2024 redesign](https://linear.app/now/how-we-redesigned-the-linear-ui), [Linear 2026 refresh](https://linear.app/now/behind-the-latest-design-refresh).

### Choose rows or cards by task

NN/g describes cards as discrete browsing units and lists as more scannable for finding and comparing information. Application: artwork grid for browsing, consistent rows for history and archive comparison, aligned values for nomination results. Avoid placing every page section inside the same visual card.

Source: [Cards: UI-Component Definition](https://www.nngroup.com/articles/cards-component/).

### Preserve recognizable controls

NN/g's flat-interface research reports greater effort when clickability cues are weak. Application: retain button boundaries, visible links and selected states while removing glows and pill overload. A restrained interface must still communicate what can be operated.

Source: [Flat UI Elements Attract Less Attention and Cause Uncertainty](https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/).

### Reveal detail after the primary task

Progressive disclosure keeps frequently needed choices visible and defers advanced detail. Recognition-oriented interfaces provide visible choices instead of requiring remembered identifiers. Application: album/schedule/discussion first, poll breakdown later; any future member picker uses recognizable names. Do not introduce a new comparison backend as part of this rework.

Sources: [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/), [Recognition and Recall](https://www.nngroup.com/articles/recognition-and-recall/).

### Clear action language and recoverable errors

GOV.UK recommends action-specific sentence-case button labels and a clear primary action. Error summaries connect validation messages to fields. Application: Open week, Open ratings in Discord, Connect Last.fm; persistent actionable request errors rather than transient toasts alone. This is interaction guidance, not a recommendation to imitate government-service branding.

Sources: [Buttons](https://design-system.service.gov.uk/components/button/), [Error summary](https://design-system.service.gov.uk/components/error-summary/).

### Readability and interaction baseline

Use WCAG 2.2 AA as the accessibility target: normal text 4.5:1, large text 3:1, minimum pointer targets of 24 CSS pixels or the specified exceptions, and reflow at 320 CSS pixels. Prefer approximately 44px touch areas for frequent mobile actions. Verify keyboard focus, dialogs, field names, and non-color state explanations. These are acceptance goals, not measurements of the existing or proposed palette.

Sources: [Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [Target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).

### Perceived speed and stability

Core Web Vitals good thresholds are LCP <=2.5s, INP <=200ms, CLS <=0.1, evaluated at the 75th percentile. Application: reserve artwork dimensions, avoid unnecessary animated surfaces, and remove list-level request fan-out. Local lab runs cannot establish field percentiles; no performance audit was completed in this research.

Source: [Web Vitals](https://web.dev/articles/vitals).

## Recommended direction and alternatives

Journal combines restrained application structure with editorial music identity. Console emphasizes dense rows, consistent columns, and compact utilities. Record store emphasizes artwork, stronger masthead typography, and visual browsing. The preview must use the same albums, counts, reviews, states, and destinations so aesthetic differences are comparable rather than confounded by content.

Research recommendation: Journal. Starting character: neutral charcoal or warm light paper, a limited coral accent, small control radii, serif album titles paired with readable sans controls, and album artwork as the main source of color.

Selection update, 2026-10-28: the owner chose Journal ("I like the Journal one;"). This establishes the visual direction; production contrast, font sizing, and responsive behavior still require verification.

## Proposed release journeys

1. Visitor opens a filtered archive -> sees sign-in -> returns to the same archive after successful authentication.
2. Member opens Overview -> identifies latest scheduled week -> opens its detail -> follows a supplied Discord thread.
3. Member searches/sorts archive -> opens a week -> returns with filters preserved.
4. Owner opens Listening -> reads stored records -> paginates without requiring profile analytics.
5. Owner opens Account -> distinguishes connected, disconnected, and unavailable states -> starts the existing supported Last.fm flow.
6. Direct visitor opens an unsupported feature URL -> receives an accurate limitation and a useful next destination.

## Review and acceptance plan

Compare overview, archive, and week detail across all three directions before finalizing tokens. Also review history, Account, signed-out, no-membership, empty, missing artwork, and request-failure states. The interactive comparison uses fictional, explicitly labeled design content with no production calls.

Later, ask actual club members to find the latest album, explain the next available action, find a past week, understand their connection state, and return from a detail screen. Record completion, mistaken expectations, and hesitation. This is a proposed evaluation plan; no participant sessions have occurred.

Implementation must map every delta-spec scenario to a named test or recorded browser check before archive. Keep appearance review distinct from backend readiness and real OAuth/deployment evidence.
