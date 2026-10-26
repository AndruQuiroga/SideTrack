# Design

## Context

Observed: Settings always supplies connections, but the shared component's optional
prop invents Last.fm linkage. Its fetch helper also collapses failure into no accounts.

## Goals / Non-Goals

Require caller data and distinguish unavailable data from an empty successful response.
Do not implement providers or alter OAuth behavior.

## Decisions

Use a required nullable connections prop. Null renders an unavailable message; an
array renders the supplied status. Extract server-side account fetching to a helper
that returns null on failure. Test real components with React server rendering and
the helper with intercepted fetch under tests/, using TypeScript's existing compiler.

## Risks / Trade-offs

The unavailable state hides connection controls until lookup recovers. This avoids
presenting an invented account state. No dependency or database change is required.
