# Tasks: 平仄模式

**Input**: `specs/002-pingze-mode/{spec.md,plan.md,research.md,data-model.md,contracts/,quickstart.md}`

**Tests**: Required. The specification explicitly requires Python/PWA parity, grammar, URL/tab-state and fixture-journey coverage.

**Organization**: Tasks are grouped by user story. Complete Phase 2 before any story phase.

## Phase 1: Setup

**Purpose**: Establish the authoritative contracts and focused test entry points.

- [ ] T001 Add pingze cases and expected non-pingze isolation cases to `contracts/relation-syntax-detect-cases.json`
- [X] T002 [P] Add dedicated pingze grammar/slot test scaffolding in `tests/test_ping_ze_serial.py` and `client/scripts/parser-self-check.ts`
- [X] T003 [P] Add pingze URL/history fixture cases in `tests/query_tabs_state_test.mjs` and `client/src/search-url.ts`

---

## Phase 2: Foundational

**Purpose**: Add shared mode/state and MatchSpec primitives that block every user story.

- [X] T004 Extend UI/URL mode metadata and localized mode labels for `pz` in `client/src/mode-meta.ts`, `client/src/mode-menu.tsx`, and `frontend/mode-i18n.mjs`
- [X] T005 Extend portable URL, browser-history and tab-frame schemas with optional `pzmode` in `frontend/query-tabs-state.mjs`, `frontend/search-navigation.mjs`, and `client/src/shared-portable.d.ts`
- [X] T006 Extend client URL helpers and tab restore plumbing for `mode=pz&pzmode=m1|m2|m3` in `client/src/search-url.ts` and `client/src/query-tabs/useQueryTabs.ts`
- [X] T007 [P] Add Python `tone_class` slot constraint and selected-mode numeric comparison support in `app/services/position_match/spec.py`, `app/services/position_match/filters/f1_slot_code.py`, and `app/utils/code_positions.py`
- [X] T008 [P] Add TypeScript `tone_class` slot constraint and selected-mode numeric comparison support in `client/src/db/position-match/spec.ts` and `client/src/db/position-match/filters/f1-slot-code.ts`
- [X] T009 Register a MatchSpec-backed pingze query kind through `contracts/query-kind-manifest.json`, `app/services/query_match_spec_registry.py`, and `client/src/db/position-match/match-spec-registry.ts`; regenerate `app/services/_generated/query_kind_registry.py` and `client/src/db/_generated/query-kind-registry.ts` with `scripts/codegen_query_kind_manifest.py`
- [X] T010 Extend Python and TypeScript candidate-filter planning so `tone_class` selects the correct length/position candidates in `app/services/position_match/` and `client/src/db/position-match/`
- [X] T011 Run foundational parser, registry and position-match checks from `tests/smoke/test_query_registry.py`, `tests/smoke/test_position_match_invariants.py`, and `client/scripts/match-spec-registry-self-check.ts`

**Checkpoint**: `pz` state can be represented and a MatchSpec can express P/Z without changing normal-mode behavior.

---

## Phase 3: User Story 1 - 搜尋平仄位置模式 (Priority: P1) 🎯 MVP

**Goal**: Let a user explicitly enter 平仄模式 and search P/Z/number/? positional patterns without intercepting Jyutping in normal modes.

**Independent Test**: In pingze mode, `PZ?`, `?PZ` and `PZ3` return only matching rows; in normal modes `p`, `z`, `pa` and `zoeng` remain Jyutping queries.

### Tests for User Story 1

- [X] T012 [P] [US1] Replace legacy global P/Z parser tests with mode-isolation and P/Z/? slot tests in `tests/test_ping_ze_serial.py`
- [ ] T013 [P] [US1] Update Python/PWA mode-detect parity coverage in `tests/smoke/test_mode_detect_parity.py` and `frontend/query-mode-detect.mjs`
- [X] T014 [P] [US1] Add TypeScript parse and MatchSpec shape assertions to `client/scripts/parser-self-check.ts` and `client/scripts/match-spec-registry-self-check.ts`

### Implementation for User Story 1

- [X] T015 [US1] Replace global pingze parsing with a mode-aware parser entry in `app/services/query_parse.py`, `app/services/query_dispatch.py`, `app/services/query_explain.py`, `app/services/ping_zak.py`, and `app/services/query_types.py`
- [X] T016 [US1] Port mode-aware pingze parsing and explanation to `client/src/db/query/parse.ts`, `client/src/db/query/engine.ts`, `client/src/db/ping-zak.ts`, `client/src/db/query-types.ts`, and `client/src/db/query-explain.ts`
- [X] T017 [US1] Remove automatic P/Z-to-394052 redirects from `app/services/query_mode_dispatch.py`, `app/services/query_dispatch.py`, `client/src/db/query/mode-dispatch.ts`, and `client/src/db/query/engine.ts`
- [X] T018 [US1] Add pingze mode/sub-mode controls and explicit query execution context to `client/src/App.tsx`, `client/src/mode-menu.tsx`, and the search hook call chain under `client/src/`
- [ ] T019 [US1] Add fixture-backed mixed-slot journey and pagination coverage in `tests/smoke/test_query_journey.py` plus a client execution self-check under `client/scripts/`
- [ ] T020 [US1] Run the US1 focused Python and client checks listed in `specs/002-pingze-mode/quickstart.md`

**Checkpoint**: P1 is independently usable: explicit 平仄模式 works for positional patterns; normal Jyutping is no longer intercepted.

---

## Phase 4: User Story 2 - 選擇數字聲調規則 (Priority: P2)

**Goal**: Let a user choose 0243, 02493 or 394052 for numeric slots while P/Z remains fixed.

**Independent Test**: The numeric slot in the same pingze query follows each selected sub-mode's existing pure-code semantics, while P/Z matches do not change.

### Tests for User Story 2

- [ ] T021 [P] [US2] Add three-sub-mode numeric-slot parity cases to `tests/test_ping_ze_serial.py` and `client/scripts/parser-self-check.ts`
- [X] T022 [P] [US2] Add URL, tab-selection, browser-history and missing-`pzmode` default cases to `tests/query_tabs_state_test.mjs` and `client/src/search-url.ts`

### Implementation for User Story 2

- [X] T023 [US2] Thread `pzmode` through Python search context, MatchSpec building and numeric slot execution in `app/services/query_dispatch.py`, `app/services/query_match_spec_registry.py`, and `app/services/position_match/`
- [X] T024 [US2] Thread `pzmode` through TypeScript search context, MatchSpec execution and mode aliases in `client/src/db/query-types.ts`, `client/src/db/query/engine.ts`, `client/src/db/query/dispatch.ts`, and `client/src/db/position-match/`
- [X] T025 [US2] Restore per-tab pingze mode and pzmode and prevent stale mode commits on sub-mode changes in `client/src/App.tsx` and `client/src/query-tabs/useQueryTabs.ts`
- [X] T026 [US2] Verify selected sub-mode behavior and share/back-forward restoration with the quickstart scenarios in `specs/002-pingze-mode/quickstart.md`

**Checkpoint**: Pingze mode preserves its chosen sub-mode across tabs, history and shared URLs, with correct numeric semantics.

---

## Phase 5: User Story 3 - 組合現有錨語法 (Priority: P3)

**Goal**: Combine pingze slots with existing literal/rhyme/missing-character operations while rejecting Jyutping anchors in pingze mode.

**Independent Test**: `PZ好=` and `?PZ好=` retain the established `好=` rhyme-anchor behavior and add their positional constraints.

### Tests for User Story 3

- [ ] T027 [P] [US3] Add grammar/fixture cases for `PZ好=`, `?PZ好=`, literal anchors, missing-character forms and invalid pingze syntax in `tests/test_ping_ze_serial.py` and `tests/smoke/test_query_journey.py`
- [ ] T028 [P] [US3] Add Python/PWA parity cases for rejected Jyutping anchors in pingze mode in `tests/smoke/test_query_explain_parity.py` and `client/scripts/parser-self-check.ts`

### Implementation for User Story 3

- [ ] T029 [US3] Compose pingze slots with existing Python rhyme/literal/missing-character builders and return the unsupported-Jyutping-anchor hint in `app/services/query_parse.py` and `app/services/query_match_spec_registry.py`
- [ ] T030 [US3] Port pingze-anchor composition and the unsupported-Jyutping-anchor hint to `client/src/db/query/parse.ts` and `client/src/db/position-match/match-spec-registry.ts`
- [ ] T031 [US3] Verify anchor explanation text and result layout in `app/services/query_explain.py`, `client/src/db/query-explain.ts`, and `tests/smoke/test_query_explain_parity.py`
- [ ] T032 [US3] Run the US3 journey/parity checks from `specs/002-pingze-mode/quickstart.md`

**Checkpoint**: All approved anchor combinations work in pingze mode; Jyutping anchors fail clearly only there.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T033 [P] Update approved terminology and examples in `CONTEXT.md`, `README.md`, `docs/README.en.md`, `docs/README.zh-Hans.md`, and `frontend/guide-i18n.mjs`
- [X] T034 [P] Add an ADR for dedicated pingze mode and mixed-slot MatchSpec under `docs/adr/`
- [ ] T035 Run the complete focused Python, Node and client checks in `specs/002-pingze-mode/quickstart.md`, plus the relevant client lint/build commands
- [ ] T036 Verify generated query-kind registry files match `contracts/query-kind-manifest.json`, review the final diff for normal-mode regressions, and update this checklist in `specs/002-pingze-mode/tasks.md`

---

## Dependencies & Execution Order

```text
Phase 1 → Phase 2 → US1 (MVP) → US2 → US3 → Polish
```

- **US1** depends on the mode/state and MatchSpec primitives in Phase 2.
- **US2** depends on US1's explicit pingze parser/execution path, then adds the persisted sub-mode semantics.
- **US3** depends on the mode-aware parser and MatchSpec path from US1/US2 so anchors compose with stable slots.
- Documentation and final verification depend on all three stories.

## Parallel Opportunities

- T002 and T003 can prepare independent test seams in parallel.
- T007 and T008 are Python/TypeScript mirror changes and can proceed in parallel after the slot contract is agreed.
- T012–T014, T021–T022 and T027–T028 are independent test files within their stories.
- T033 and T034 are independent documentation changes after behavior is stable.

## Implementation Strategy

1. Deliver the explicit mode and P/Z/? MatchSpec path first (US1), then run its independent tests.
2. Add pzmode's three numeric semantics and state restoration (US2), then verify URLs/tabs.
3. Add anchor composition and the explicit Jyutping-anchor rejection (US3).
4. Update user-facing documentation and run the full focused validation suite.

All tasks use the required checklist format, include exact file paths, and are dependency ordered.
