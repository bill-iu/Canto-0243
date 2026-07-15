/**
 * Port of app/services/query_grammar/mask.py — thin re-export.
 * SSOT: client/src/db/query/grammar/mask.ts
 */
export {
  isWildcardChar,
  parseMaskQuery,
  buildMaskFromSlots,
} from '../query/grammar/mask.ts';
