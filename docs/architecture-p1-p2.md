# Architecture P1/P2 implementation

Scope approved after the architecture review: preserve the existing single-line
product workflow while improving its underlying contracts. No new dependencies.

1. Replace mutable TypeScript rhyme-profile state with explicit execution context
   through candidate retrieval, filtering and ranking. Test overlapping requests.
2. Separate durable work content from session controls in a versioned document
   envelope. Keep legacy session/draft import, recovery, and one-step undo. Expose
   validated import/export through the same storage module; defer multi-song UI.
3. Add focused behavior checks to CI, including fast Python canonical contracts on
   dev pushes. Keep source checks only where they protect architectural boundaries.
4. Extract cohesive shell/navigation and workbench input responsibilities from
   page components, retaining existing coordinators and interaction contracts.
5. Move legacy MatchSpec exports out of the public query facade into an explicit
   compatibility module; retain adapters still used by migration tests.
6. Extend the existing benchmark tooling with representative query/workbench
   cases and machine-readable measurements. Distinguish fixture diagnostics from
   real-lexicon/browser measurements; do not claim speedups without measurements.

Validation: TypeScript, affected self-checks, Python contracts/smoke, portable
build and existing CI checks. Commit and push to dev; main requires user approval.

## Implemented boundaries

- Search and workbench pass their rhyme profile to SQL/index candidate selection,
  every phoneme/letter filter and exact-first candidate ranking. The mutable TS
  context is deleted. Multi-anchor narrowing now retains loose-profile matches.
- Storage v2 separates current content from editor controls. `session/storage.ts`
  is the shared load/save/import/export boundary; `session/document.ts` owns the
  envelope, and `session/codec.ts` owns validation/legacy normalization. Loading
  does not write a migration until a successful save. See ADR-0081.
- `useWorkbenchInput` owns manual text entry and ingestion; `useWorkbenchTransfer`
  owns shell handoff. The existing session coordinator still owns state. A late
  async rhyme UI subscription was replaced by synchronous subscription/cleanup.
- Legacy query exports moved to `query-engine-legacy.ts`; the adapter test uses
  that entry. An unreachable duplicate dispatch branch was removed.
- The existing relation-pool builder failed its 350-line architecture check before
  this change. Its independent embedding-neighbor reader is now a separate module;
  ranking, pool merge behavior and the existing size guard remain unchanged.
- Removed an existing unused `MAGIC` constant that blocked TypeScript checking.

## Repeatable performance baseline

From `client/`:

```text
npx tsx scripts/architecture-benchmark.ts ../tests/fixtures/lyrics.db ../logs/architecture-benchmark-fixture.json
npx tsx scripts/architecture-benchmark.ts ../lyrics.db ../logs/architecture-benchmark-full.json
```

The runner opens an in-memory copy; it does not modify the lexicon. Reports include
commit, dirty-tree status, runtime/CPU, dataset size/count, open/auxiliary load times,
first/repeat query timings, unanchored workbench snapshot timings, event-loop delay
and sampled heap. Run independently of other builds for comparable results.

For on-device PWA measurement, use the existing `?benchmark` page. The workbench
probe uses the real PWA adapter, including OPFS Worker execution when available.
The benchmark UI is lazy-loaded and excludes concurrent StrictMode runs. Inspect
startup.cache to distinguish downloaded and cached opens: resetting the runtime
does not delete OPFS/SW data. Capture first-visit and warm/offline runs separately.
Unsupported heap reporting is null; sampled heap excludes Worker/WASM memory.

2026-09-18 local observation: Node 22.18.0 / Windows x64 / i7-9700K / sql.js,
40,108,032-byte lexicon, 181,222 rows, one run with the working tree modified:

| Case | First (ms) | Repeat (ms) |
| --- | ---: | ---: |
| Lookup 香港, first 400 rows | 502.2 | 498.6 |
| Dense code 30, first 400 rows | 152.7 | 146.8 |
| Wildcard 香?? | 23.0 | 19.8 |
| Exact whole-word rhyme 香港= | 2.9 | 2.3 |
| Loose whole-word rhyme 香港= | 1634.9 | 1.9 |
| Unanchored 2-slot snapshot, 70,900 distinct candidates | 2978.7 | 1.7 |
| Unanchored 4-slot snapshot, 28,952 distinct candidates | 1727.5 | 2.3 |

These are an initial diagnostic baseline, not before/after improvement figures or
browser responsiveness claims. Node does not enable the browser-only cooperative
yielding path. Future performance work should first measure the real device/backend
and examine first snapshot construction and literal lookup.

The measurements also surfaced a pre-existing whole-word loose-rhyme anomaly:
香港= returned 1 distinct result in tong versus 91 in exact. The whole-word loose
branch still applies `ref_literal` containment when `phoneme_anchor_only` is false.
This semantic issue was not changed by the context refactor; it needs a separate
Python/TS parity regression before changing the whole-word contract.

## Verification

- Frontend CI harness: 30 checks passed (including new overlap/storage checks).
- Python fast contracts: 31 passed.
- Full Python smoke: 240 tests, 4 skipped, no failures after module extraction.
- Architecture seams: 89 tests, 6 skipped, no failures.
- TypeScript, portable build, generated translation freshness and diff whitespace
  checks passed. Full fixture and full-lexicon baseline runners completed.
- Real-device cold/warm OPFS/Safari measurements have not been performed here.
