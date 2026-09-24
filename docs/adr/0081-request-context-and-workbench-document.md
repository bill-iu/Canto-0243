# ADR-0081: Explicit rhyme context and versioned workbench documents

Status: accepted
Date: 2026-09-18

## Decision

TypeScript search and workbench execution carry `rhymeProfile` explicitly through
candidate retrieval, phoneme filtering and ranking. No mutable module-level
profile is permitted across `await`. Python retains its existing `ContextVar`
scope. The immutable CanonicalMatchSpec compiler contract (ADR-0076) is unchanged;
the execution context supplies the orthogonal rhyme profile (ADR-0078).

The public query facade exposes canonical compilation/execution. Legacy builders
and conversion exports live in `query-engine-legacy.ts` for migration callers and
tests; they do not become an alternative production compiler.

Persisted workbench payload v2 separates current line content (surface, selected
readings and codes) from editor state (locks, selection, replacement controls and
undo). It uses the existing storage key and one atomic `setItem` for the complete
envelope. Session v1 and draft v1 load in memory and migrate on successful save.
The shared codec validates file imports and runtime persistence identically.
No multi-song UI, IndexedDB dependency or additional history semantics are added.

Automatic save/clear refuses to overwrite an unreadable or future-version payload.
Loading retains its full raw value as recovery when storage permits, always leaving
the original intact. An explicit validated import first retains the previous
payload before replacing it. If backup or save fails, the current value survives.

## Verification

- Interleaved exact/loose searches and workbench snapshots remain independent.
- Multiple rhyme anchors expand before narrowing; loose-only candidates survive.
- Legacy migration, round-trip content/readings/locks/undo, invalid imports, full
  storage and future-version preservation are checked through the storage API.
- Dev pushes run Python compiler/phoneme/workbench contracts and the new TS checks.
- Performance diagnostics report dataset/runtime metadata, first/repeat query
  and snapshot times, event-loop delay and sampled JS heap. They are observations,
  not hardware-independent timing gates or assertions of a speedup.
