# ADR-0076: Canonical MatchSpec compiler seam

Status: accepted  
Date: 2026-07-26  
Supersedes: [ADR-0046](./0046-query-dispatch-seams-and-ssot.md)

## Decision

The query grammar owns parsing only. A single compiler module owns the
`ParsedQuery → CanonicalMatchSpec` transformation for every query kind marked
`match_spec` in the generated manifest. Workbench replacement plans use a
separate `compileReplacementPlan` input adapter and the same finalizer.

`CanonicalMatchSpec` is an immutable semantic value. It owns width, ordered
slot constraints, the derived mask, equals span, compound policy, ranking
policy, candidate scope, code mode, and explicit dual phoneme branches. The
finalizer validates width, slot positions, duplicate constraints, mask width,
and equals-span positions before execution.

Execution chooses a physical candidate source from this semantic value. It
does not parse raw query text, rebuild a spec, or inspect an open-ended
`extra` dictionary as a second source of truth. During migration, the
canonical-to-legacy adapter is the only seam allowed to feed the old filters;
callers already on the canonical interface must not use the registry wrapper.

## Rationale

The compiler is a deep module: callers get one complete value and do not need
to know grammar-specific slot placement. The interface is the test surface;
Python and TypeScript are checked against `contracts/match-spec-cases.json`.
This keeps locality in the compiler and gives candidate-source planning a
stable semantic input without coupling it to SQL, OPFS, sql.js, or ORM details.

Candidate scope is semantic: `bounded` permits the normal source cap, while
`complete` requires the execution adapter to expose the full width bucket for
workbench snapshots. It is not a backend flag and must not be inferred from a
caller-specific mutable dictionary.

## Consequences

- New query families add one compiler branch and golden cases rather than
  another grammar builder plus registry entry.
- The legacy registry and grammar `toMatchSpec` functions remain migration
  code until all execution callers leave the adapter; they are not production
  authority.
- Immutable specs can be reused by paging and load-more sessions without
  mutation or reparsing.
- A shared corpus catches Python/TypeScript drift before an execution change is
  reviewed.

## Verification

The canonical compiler self-check covers all declared MatchSpec families,
pure Han lookup rejection, equals spans, sparse anchors, literal refs,
Jyutping dual branches, Ping/Ze overlays, compounds, and workbench plan
parity.
