import { normalizeAndParse } from '../src/db/query-engine.ts';
import { buildMatchSpecForParsed } from '../src/db/position-match/match-spec-registry.ts';

for (const q of ['?30人', '?+人=?', '?3人=?', '23就=']) {
  const p = normalizeAndParse(q);
  const s = buildMatchSpecForParsed(p);
  console.log(q, p.kind, s?.width, s?.mask, s?.slots?.length);
}
