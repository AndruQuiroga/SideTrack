# Safe Browsing launch blocker — 2026-10-28

The owner reported Chrome's **Dangerous site** phishing warning on the return
from Discord authorization. Do not bypass the warning or disable protection.

## Observed evidence

- Google's public report for `sidetrack.network` says **Some pages on this site
  are unsafe**, with **last updated September 12, 2025**. That predates this
  deployment. It suggests a historical domain issue; it does not establish that
  the current site is safe or identify the original affected pages.
- The Cloudflare zone was created 2026-10-28 04:40 UTC; it is active. Root/API
  records point to the expected tunnel. `www` remains on the preserved Squarespace
  target `ext-sq.squarespace.com`; its previous content has not been audited.
  Cloudflare's own `phishing_detected` field is false, which does not override
  Google's classification.
- Cloudflare lists no Worker routes or Page Rules for this zone; returned
  rulesets are Cloudflare-managed security and normalization rules.
- PR #297 fixes the separate Discord issuer error. All eight PR checks passed;
  merged commit is `915315aa2f8207632c1ee3db30ddf3dacd040c83`. Main CI run
  `40643863367` passed all eight checks and published the web image.
- Portainer stack 23 now pins only web to
  `ghcr.io/andruquiroga/sidetrack-web@sha256:4a3b4b994ddbb9d939293e95b3cc7c244396dff3bb562d3a311f3d6eecaa0c23`.
  Its OCI revision matches the merged commit; authentication config, login,
  OAuth buttons and service-worker source hashes match the tested source.
- The container is healthy, with no runtime file changes outside expected
  `/root` package caches, `/run` secret mounts and `/tmp` compile caches.
  This is a limited integrity check, not a complete security assessment.
- Local web lint, production build and all 22 tests passed. Real Discord
  completion and Last.fm linking remain unverified. Chrome reached official
  Discord authorization, then blocked the callback with its warning.
- The currently signed-in Google Search Console account has no accessible
  property selected. No domain verification, ownership grant or review request
  has been submitted through Search Console. No callback codes, state values or
  tokens are recorded here.

## Submitted review text

> Please reassess https://sidetrack.network/ and /api/auth/callback/discord.
> I operate SideTrack, a music-club app using Discord OAuth. Your public report
> was last updated September 12, 2025; the current app was deployed October
> 27–28, 2026. Sign-in redirects to Discord's official authorization service and
> receives its callback. The app does not request Discord passwords or offer
> software downloads. Deployed authentication files match the reviewed,
> CI-tested release, and integrity checks found no application-file changes.
> Chrome blocks the return from Discord. The public report does not identify
> the historical affected URLs; please review the current content.

The owner explicitly approved submission. The Safe Browsing report form was
submitted for `https://sidetrack.network/api/auth/callback/discord` on 2026-10-28
and visibly confirmed **Submission was successful**. No CAPTCHA challenge was
presented. The form disclosed account/system information sharing with Google and
possible publication/sharing of the URL and its status. No case ID was displayed.
The screenshot is saved locally at `.tmp/google-safe-browsing-review-submitted.png`.
This confirms receipt only; Google has not yet cleared the classification.

Before claiming the issue resolved, inspect Search Console's sample URLs if
available, address every affected host/page, obtain Google's review result, and
repeat Discord sign-in and Last.fm linking with browser protection enabled.

References:
- [Public domain report](https://transparencyreport.google.com/safe-browsing/search?url=sidetrack.network)
- [Google security issues workflow](https://support.google.com/webmasters/answer/9044101?hl=en)
- [Google Safe Browsing review form](https://safebrowsing.google.com/safebrowsing/report_error/?hl=en)
