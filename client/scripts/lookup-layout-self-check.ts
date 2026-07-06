/** ponytail: one-shot lookup layout self-check */
import { lookupLayoutSelfCheck } from '../src/db/query-engine.ts';

await lookupLayoutSelfCheck();
console.log('lookup layout self-check ok');
