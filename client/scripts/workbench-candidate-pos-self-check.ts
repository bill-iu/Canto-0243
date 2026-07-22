/**
 * POS over-fetch + dense-code unlimited (貪婪→金錢).
 * Over-fetch lives in candidate-session (P2#4); hook is thin shell.
 */
import fs from 'node:fs';

const hook = fs.readFileSync('src/workbench/useWorkbenchCandidates.ts', 'utf8');
const session = fs.readFileSync('src/workbench/candidate-session/session.ts', 'utf8');
const engine = fs.readFileSync('src/db/position-match/engine.ts', 'utf8');
const pySources = fs.readFileSync('../app/services/position_match/sources.py', 'utf8');
const adr = fs.readFileSync('../docs/adr/0064-workbench-candidate-page-size.md', 'utf8');

if (!hook.includes('candidate-session') || !hook.includes('runCandidateFetch')) {
  throw new Error('useWorkbenchCandidates must delegate to candidate-session');
}
if (!session.includes('filteredTarget') || !session.includes('runCandidateFetch')) {
  throw new Error('candidate-session must over-fetch via filteredTarget');
}
if (!session.includes('applyCreatorPosFilter')) {
  throw new Error('candidate-session must apply creator POS filter');
}
if (!engine.includes('Boolean(code)') || !engine.includes('unlimited:')) {
  throw new Error('executeMatchSpec must unlimited-load dense code buckets');
}
if (!pySources.includes('fallback_limit=None') || !pySources.includes('effective_code.isdigit()')) {
  throw new Error('Python LengthCode dense-code path must skip LIMIT 2000');
}
if (!adr.includes('auto over-fetch') && !adr.includes('over-fetch')) {
  throw new Error('ADR-0064 must document POS over-fetch');
}

console.log('workbench candidate POS self-check ok');
