export type WorkbenchSlotKind =
  | 'code_digit'
  | 'literal_char'
  | 'final_anchor'
  | 'initial_anchor'
  | 'tone_class';

export interface WorkbenchSlotConstraintV1 {
  pos: number;
  kind: WorkbenchSlotKind;
  digit?: string;
  literal?: string;
  ref?: string;
  refJyutping?: string;
  toneClass?: 'ping' | 'ze';
}

/** Single request page size / max limit (ADR-0064). */
export const WORKBENCH_CANDIDATE_PAGE_SIZE = 400;

export interface ReplacementPlanV1 {
  version: 1;
  selectionVersion: number;
  width: number;
  mode: 'm1' | 'm2' | 'm3';
  slots: WorkbenchSlotConstraintV1[];
  semanticIntent: 'ranked' | 'direct_only' | 'off';
  semanticSeed?: string;
  limit: number;
  /** 0-based row offset into the sorted MatchSpec pool (default 0). */
  offset?: number;
}

export type CandidateGroup = 'direct_syn' | 'semantic_related' | 'sound_only';

export type CandidateReasonKind =
  | 'tone_exact'
  | 'tone_loose'
  | 'literal_match'
  | 'same_final'
  | 'same_initial'
  | 'direct_syn'
  | 'semantic_related'
  | 'frequency_rank'
  | 'relaxed_constraint';

export interface CandidateReason {
  kind: CandidateReasonKind;
  positions: number[];
  source?: string;
}

export interface WorkbenchCandidate {
  literal: string;
  jyutping: string;
  code: string;
  group: CandidateGroup;
  reasons: CandidateReason[];
  sourceRank: number;
  relaxationId?: string;
}

export interface CandidateGroups {
  direct_syn: WorkbenchCandidate[];
  semantic_related: WorkbenchCandidate[];
  sound_only: WorkbenchCandidate[];
}

export type RelaxationKind =
  | 'semantic_ranked'
  | 'remove_final'
  | 'remove_initial'
  | 'remove_code'
  | 'loosen_mode';

export interface RelaxationSuggestion {
  id: string;
  kind: RelaxationKind;
  positions?: number[];
  from?: string;
  to?: string;
  candidateCount: number;
  plan: ReplacementPlanV1;
}

export interface WorkbenchCandidateResponse {
  version: 1;
  selectionVersion: number;
  exact: CandidateGroups;
  /** Engine pool size before POS filter / before this page slice (ADR-0064). */
  total: number;
  relaxation?: RelaxationSuggestion | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`invalid ReplacementPlanV1: ${message}`);
}

function parseSlot(value: unknown, width: number): WorkbenchSlotConstraintV1 {
  assert(isRecord(value), 'slot must be an object');
  assert(Number.isInteger(value.pos) && Number(value.pos) >= 0 && Number(value.pos) < width, 'slot pos');
  const kinds: WorkbenchSlotKind[] = [
    'code_digit',
    'literal_char',
    'final_anchor',
    'initial_anchor',
    'tone_class',
  ];
  assert(kinds.includes(value.kind as WorkbenchSlotKind), 'slot kind');
  const slot = value as unknown as WorkbenchSlotConstraintV1;
  if (slot.kind === 'code_digit') assert(/^\d$/.test(slot.digit ?? ''), 'slot digit');
  if (slot.kind === 'literal_char') assert((slot.literal ?? '').length === 1, 'slot literal');
  if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') {
    assert(Boolean(slot.ref), 'slot ref');
    if (slot.refJyutping != null) assert(Boolean(slot.refJyutping.trim()), 'slot refJyutping');
  }
  if (slot.kind === 'tone_class') assert(slot.toneClass === 'ping' || slot.toneClass === 'ze', 'tone class');
  return { ...slot };
}

export function parseReplacementPlanV1(value: unknown): ReplacementPlanV1 {
  assert(isRecord(value), 'plan must be an object');
  assert(value.version === 1, 'version');
  assert(Number.isInteger(value.selectionVersion) && Number(value.selectionVersion) >= 0, 'selectionVersion');
  assert(Number.isInteger(value.width) && Number(value.width) >= 1 && Number(value.width) <= 4, 'width');
  assert(value.mode === 'm1' || value.mode === 'm2' || value.mode === 'm3', 'mode');
  assert(Array.isArray(value.slots), 'slots');
  assert(
    value.semanticIntent === 'ranked' || value.semanticIntent === 'direct_only' || value.semanticIntent === 'off',
    'semanticIntent',
  );
  assert(
    Number.isInteger(value.limit)
      && Number(value.limit) >= 1
      && Number(value.limit) <= WORKBENCH_CANDIDATE_PAGE_SIZE,
    'limit',
  );
  const offset = value.offset == null ? 0 : Number(value.offset);
  assert(Number.isInteger(offset) && offset >= 0, 'offset');
  if (value.semanticSeed != null) {
    assert(typeof value.semanticSeed === 'string' && value.semanticSeed.length >= 1 && value.semanticSeed.length <= 4, 'semanticSeed');
  }
  const width = Number(value.width);
  return {
    version: 1,
    selectionVersion: Number(value.selectionVersion),
    width,
    mode: value.mode,
    slots: value.slots.map((slot) => parseSlot(slot, width)),
    semanticIntent: value.semanticIntent,
    semanticSeed: value.semanticSeed as string | undefined,
    limit: Number(value.limit),
    offset,
  };
}

const REASON_KINDS: CandidateReasonKind[] = [
  'tone_exact',
  'tone_loose',
  'literal_match',
  'same_final',
  'same_initial',
  'direct_syn',
  'semantic_related',
  'frequency_rank',
  'relaxed_constraint',
];

const GROUPS: CandidateGroup[] = ['direct_syn', 'semantic_related', 'sound_only'];
const RELAXATION_KINDS: RelaxationKind[] = [
  'semantic_ranked',
  'remove_final',
  'remove_initial',
  'remove_code',
  'loosen_mode',
];

function parseReason(value: unknown): CandidateReason {
  assert(isRecord(value), 'candidate reason must be structured');
  assert(REASON_KINDS.includes(value.kind as CandidateReasonKind), 'candidate reason kind');
  assert(Array.isArray(value.positions), 'candidate reason positions');
  const positions = value.positions.map((pos) => {
    assert(Number.isInteger(pos) && Number(pos) >= 0 && Number(pos) <= 3, 'candidate reason pos');
    return Number(pos);
  });
  assert(value.source == null || (typeof value.source === 'string' && value.source.length > 0), 'candidate reason source');
  return { kind: value.kind as CandidateReasonKind, positions, source: value.source as string | undefined };
}

function parseCandidate(value: unknown, group: CandidateGroup): WorkbenchCandidate {
  assert(isRecord(value), 'candidate');
  assert(typeof value.literal === 'string' && value.literal.length >= 1 && value.literal.length <= 4, 'candidate literal');
  assert(typeof value.jyutping === 'string', 'candidate jyutping');
  assert(typeof value.code === 'string', 'candidate code');
  assert(value.group === group, 'candidate group');
  assert(Array.isArray(value.reasons) && value.reasons.length > 0, 'candidate reasons');
  assert(Number.isInteger(value.sourceRank) && Number(value.sourceRank) >= 0, 'candidate sourceRank');
  return {
    literal: value.literal,
    jyutping: value.jyutping,
    code: value.code,
    group,
    reasons: value.reasons.map(parseReason),
    sourceRank: Number(value.sourceRank),
    relaxationId: value.relaxationId as string | undefined,
  };
}

function parseGroups(value: unknown): CandidateGroups {
  assert(isRecord(value), 'candidate groups');
  assert(Object.keys(value).length === GROUPS.length && Object.keys(value).every((key) => GROUPS.includes(key as CandidateGroup)), 'candidate group keys');
  const parse = (group: CandidateGroup) => {
    const rows = value[group];
    assert(Array.isArray(rows), `candidate group ${group}`);
    return rows.map((row) => parseCandidate(row, group));
  };
  return {
    direct_syn: parse('direct_syn'),
    semantic_related: parse('semantic_related'),
    sound_only: parse('sound_only'),
  };
}

function parseRelaxation(value: unknown): RelaxationSuggestion {
  assert(isRecord(value), 'candidate response relaxation');
  assert(typeof value.id === 'string' && value.id.length > 0, 'relaxation id');
  assert(RELAXATION_KINDS.includes(value.kind as RelaxationKind), 'relaxation kind');
  assert(Number.isInteger(value.candidateCount) && Number(value.candidateCount) >= 1, 'relaxation candidateCount');
  const positions = value.positions == null
    ? undefined
    : (() => {
        assert(Array.isArray(value.positions), 'relaxation positions');
        return value.positions.map((pos) => {
          assert(Number.isInteger(pos) && Number(pos) >= 0 && Number(pos) <= 3, 'relaxation pos');
          return Number(pos);
        });
      })();
  assert(value.from == null || typeof value.from === 'string', 'relaxation from');
  assert(value.to == null || typeof value.to === 'string', 'relaxation to');
  return {
    id: value.id,
    kind: value.kind as RelaxationKind,
    positions,
    from: value.from as string | undefined,
    to: value.to as string | undefined,
    candidateCount: Number(value.candidateCount),
    plan: parseReplacementPlanV1(value.plan),
  };
}

export function parseWorkbenchCandidateResponse(value: unknown): WorkbenchCandidateResponse {
  assert(isRecord(value), 'candidate response');
  assert(value.version === 1, 'candidate response version');
  assert(Number.isInteger(value.selectionVersion) && Number(value.selectionVersion) >= 0, 'candidate response selectionVersion');
  assert(Number.isInteger(value.total) && Number(value.total) >= 0, 'candidate response total');
  const relaxation = value.relaxation == null ? null : parseRelaxation(value.relaxation);
  return {
    version: 1,
    selectionVersion: Number(value.selectionVersion),
    exact: parseGroups(value.exact),
    total: Number(value.total),
    relaxation,
  };
}
