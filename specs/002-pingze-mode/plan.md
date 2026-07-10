# Implementation Plan: 平仄模式

**Branch**: `dev` | **Date**: 2026-07-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification at `specs/002-pingze-mode/spec.md` and approved design at `docs/superpowers/specs/2026-07-10-pingze-mode-design.md`.

## Summary

Replace global P/Z auto-detection with an explicit 平仄 UI mode. The mode stores an independent 0243-family sub-mode, compiles `P`／`Z`／number／`?` positions and existing anchors into the shared MatchSpec path, and preserves the chosen state in tabs, history and URLs. `P` and `Z` always inspect the stored 394052 digit; numeric positions reuse the selected sub-mode's existing code-variant semantics.

## Technical Context

**Language/Version**: Python runtime (repository requirements are unpinned); TypeScript 6; React 19; Node-based build tooling

**Primary Dependencies**: FastAPI, SQLAlchemy, Vite, React, sql.js, wa-sqlite

**Storage**: Existing SQLite lexicon and browser OPFS/cache; no schema migration

**Testing**: Python `unittest`; Node test runner; TypeScript self-check scripts invoked with `tsx`

**Target Platform**: Python service and offline-capable browser PWA

**Project Type**: Dual Python service plus TypeScript PWA port sharing query semantics

**Performance Goals**: Preserve existing length-bucket candidate filtering, ordering, deduplication and pagination; do not implement P/Z by expanding one query into multiple full searches

**Constraints**: P/Z classification is fixed to 394052; numeric slots follow only the selected sub-mode; non-pingze modes must not detect or redirect P/Z; Jyutping anchors are rejected only in pingze mode

**Scale/Scope**: One new search mode, three existing sub-mode choices, shared parser/matcher/URL/tab contract across Python and PWA

## Constitution Check

`.specify/memory/constitution.md` remains the unfilled repository template, so it supplies no enforceable project-specific gates. The feature still follows the repository's documented guardrails: stay on `dev`, preserve Python/PWA parity, use the existing MatchSpec path, and retain the current search result behavior.

**Pre-design gate**: PASS — no new storage, external service, privilege, or unbounded query path is required.

## Project Structure

### Documentation (this feature)

```text
specs/002-pingze-mode/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── pingze-query-grammar.md
    └── pingze-url-state.md
```

### Source Code (repository root)

```text
app/services/
├── ping_zak.py
├── query_parse.py
├── query_dispatch.py
├── query_mode_dispatch.py
├── query_types.py
├── query_match_spec_registry.py
└── position_match/
    ├── spec.py
    └── filters/f1_slot_code.py

client/src/
├── App.tsx
├── mode-meta.ts
├── mode-menu.tsx
├── search-url.ts
├── query-tabs/useQueryTabs.ts
└── db/
    ├── ping-zak.ts
    ├── query/{parse.ts,engine.ts,dispatch.ts,mode-detect.ts,mode-dispatch.ts}
    └── position-match/{spec.ts,match-spec-registry.ts,filters/f1-slot-code.ts}

frontend/
├── query-tabs-state.mjs
├── search-navigation.mjs
├── mode-i18n.mjs
└── query-mode-detect.mjs

tests/
├── test_ping_ze_serial.py
├── smoke/{test_mode_detect_parity.py,test_query_journey.py,test_position_match_invariants.py}
└── query_tabs_state_test.mjs
```

**Structure Decision**: Extend the existing dual-port query system and shared portable state modules. The feature introduces no new application or storage layer.

## Phase 0: Research Decisions

See [research.md](research.md). All research questions are resolved:

1. Use an explicit `pingze` mode rather than global P/Z syntax detection.
2. Compile mixed slots to MatchSpec rather than create another executor.
3. Add a `tone_class` positional constraint for `ping`／`ze`.
4. Pass selected pingze sub-mode only to numeric constraints; P/Z inspect 394052 directly.
5. Persist `mode=pz` and `pzmode=m1|m2|m3` in URL/history/tab frames.
6. Reject Jyutping anchors in pingze parser before generic Jyutping parsing can claim them.

## Phase 1: Design

See [data-model.md](data-model.md), [query grammar contract](contracts/pingze-query-grammar.md), [URL-state contract](contracts/pingze-url-state.md), and [quickstart.md](quickstart.md).

## Implementation Outline

1. **Shared mode contract**
   - Add `pz` to UI/URL modes and localized mode metadata/menu/guide content.
   - Define `pzmode` values as existing `m1`/`m2`/`m3`; default an inbound `mode=pz` URL without `pzmode` to `m1`.
   - Extend portable URL parsing/building, search-navigation frame, tab history serialization, TypeScript declarations, app URL helpers and tab restore so mode and pzmode move together.

2. **Remove global P/Z behavior**
   - Remove P/Z detection from normal parser classification and all automatic 394052 redirects in Python, TypeScript, synonym-mode dispatch and `App.tsx`.
   - Retire or narrow the legacy PingZeSerial route so it cannot intercept ordinary P/Z or Jyutping input outside pingze mode.

3. **Define mode-aware pingze parsing**
   - Add a dedicated parse entry used by search execution and query explanation when context mode is pingze.
   - Parse P, Z, number and `?` as positional slot conditions while retaining existing outer grammar precedence for literals, rhyme anchors and missing-character syntax.
   - Emit a dedicated unsupported-Jyutping-anchor hint in pingze mode and a dedicated invalid-pingze-syntax hint for other invalid combinations.

4. **Extend MatchSpec and matching**
   - Add `tone_class: ping|ze` to Python and TypeScript slot constraint types.
   - Compile pingze parsed queries into a MatchSpec-backed query kind and route it through the existing mask-family path.
   - Extend candidate-filter planning and per-slot filtering: `ping` matches 394052 0/3; `ze` matches any other stored 394052 digit; numeric constraints use the normalized selected pzmode.
   - Compose these constraints with existing literal and final/rhyme-anchor constraints; leave `?` unconstrained.

5. **Wire UI runtime behavior**
   - Add explicit mode selection and a visible pingze-only sub-mode selector.
   - On entry, inherit the currently/recently selected 0243-family mode; on sub-mode change, commit the new frame without stale React mode state.
   - Restore each selected tab's stored mode and pzmode before issuing its search; preserve the pair on popstate and guide example navigation.

6. **Parity, regression and documentation**
   - Update the query-kind manifest/registries with their generator, not hand-maintained generated files.
   - Replace legacy auto-detect tests with explicit mode-isolation and mixed-slot tests in both ports.
   - Add fixture journey tests, URL/tab round-trips and TypeScript self-check coverage.
   - Update `CONTEXT.md`, README and guide copy; create an ADR that records the dedicated mode and MatchSpec decision.

## Post-Design Constitution Check

PASS — the design uses existing query and storage paths, preserves dual-port parity, and confines new behavior to an explicit mode. The added state is small, serializable search context; no complexity exception is required.

## Complexity Tracking

No constitution violations or additional project layers require justification.
