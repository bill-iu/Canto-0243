/**
 * ponytail: guide example labels must equal query-explain summaries.
 * Run: npx tsx client/scripts/guide-explain-labels-self-check.ts
 */
import { getGuideSections } from '../src/guide-examples.ts';
import { explainQuery } from '../src/db/query-explain.ts';
import { uiModeToExplainMode } from '../src/hooks/useQueryExplain.tsx';

const modeToExplain: Record<string, string> = {
  '0243': 'm1',
  '02493': 'm2',
  '394052': 'm3',
  synonym: 'syn',
  pingze: 'pz',
};

let failed = 0;
for (const section of getGuideSections('zh')) {
  for (const ex of section.examples) {
    const mode = modeToExplain[ex.mode] || uiModeToExplainMode(ex.mode);
    const summary = explainQuery(ex.query, mode).summary;
    if (!summary) {
      console.error(`FAIL ${section.id}:${ex.query} — empty explain`);
      failed += 1;
      continue;
    }
    if (ex.label !== summary) {
      console.error(`FAIL ${section.id}:${ex.query}\n  label:   ${ex.label}\n  explain: ${summary}`);
      failed += 1;
    }
  }
}

if (failed) {
  console.error(`guide-explain-labels-self-check: ${failed} mismatch(es)`);
  process.exit(1);
}
console.log('guide-explain-labels-self-check ok');
