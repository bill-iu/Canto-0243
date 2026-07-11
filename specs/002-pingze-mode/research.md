# Research: 平仄模式

## Decision: explicit pingze mode, not automatic P/Z recognition

**Rationale**: Current Python and TypeScript `ping_zak` parsers recognise `[PZ0-9]+` globally, then redirect execution to 394052. This captures legitimate Jyutping `p`／`z` input. An explicit mode isolates the syntax and removes all automatic redirects.

**Alternatives considered**:

- Uppercase-only P/Z retains a hidden, fragile case-sensitive language boundary.
- A `pz:` prefix avoids the collision but makes a first-class filling workflow unnecessarily cumbersome.

## Decision: MatchSpec-backed pattern rather than a bespoke executor

**Rationale**: The current P/Z serial route has its own full-length-bucket executor and cannot compose with `?`, rhyme anchors or literal anchors. Existing MatchSpec already composes positional code, literal and phoneme/rhyme constraints, then retains common ordering, deduplication and pagination.

**Alternatives considered**:

- Add an executor for every existing grammar family: duplicates precedence and drifts between Python/PWA.
- Expand P/Z into multiple numeric queries: loses selected-mode semantics and makes ranking/pagination incorrect.

## Decision: a new tone-class slot constraint

**Rationale**: `P` and `Z` are neither literal characters nor numeric code variants. A `tone_class` constraint cleanly expresses `ping` (stored 394052 digit 0 or 3) and `ze` (all other digits) alongside existing slot constraints.

**Alternatives considered**:

- Treat P/Z as literal mask characters: existing mask matching would interpret them as literal text, not tones.
- Encode all tone choices in the parser: creates query expansion and bypasses shared slot filtering.

## Decision: split P/Z and numeric comparison context

**Rationale**: P/Z must always inspect stored 394052 digits, while a numeric slot must reuse the selected `m1`, `m2` or `m3` variant rules. The match context therefore carries both the explicit pingze sub-mode and the fixed P/Z mapping.

**Alternatives considered**:

- Force all pingze searches to m3: contradicts the approved three sub-mode interaction.
- Make P/Z follow sub-mode: changes their user-visible meaning.

## Decision: persist pzmode in search frames and URLs

**Rationale**: Search tabs and history currently preserve only query plus mode. A pingze query without pzmode cannot be replayed reliably. The canonical URL is `mode=pz&pzmode=m1|m2|m3&q=…`; a missing pzmode defaults to m1 for compatibility.

**Alternatives considered**:

- Keep pzmode only in React state: tab switches, back/forward and share links lose it.
- Encode pzmode into query text: pollutes query grammar and cannot support existing links.

## Decision: reject Jyutping anchors only in pingze mode

**Rationale**: The feature deliberately reserves P/Z in pingze mode. A clear mode-specific hint prevents ambiguous anchor parsing while normal modes retain all existing Jyutping behavior.

## Verified existing seams

- Legacy parser/executor: `app/services/ping_zak.py`, `client/src/db/ping-zak.ts`, `app/services/query_parse.py`, `client/src/db/query/parse.ts`.
- MatchSpec registry/filter: `app/services/query_match_spec_registry.py`, `app/services/position_match/filters/f1_slot_code.py`, `client/src/db/position-match/match-spec-registry.ts`, `client/src/db/position-match/filters/f1-slot-code.ts`.
- UI/state: `client/src/mode-meta.ts`, `client/src/App.tsx`, `frontend/query-tabs-state.mjs`, `frontend/search-navigation.mjs`, `client/src/query-tabs/useQueryTabs.ts`.
- Existing verification: `tests/test_ping_ze_serial.py`, `tests/smoke/test_mode_detect_parity.py`, `tests/smoke/test_query_journey.py`, `tests/query_tabs_state_test.mjs`, and client parser/match-spec/PWA self-check scripts.
