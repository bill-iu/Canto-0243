/** ADR-0032: gate progress weights */
import {
  reportGatePhase,
  subscribeGateProgress,
} from '../src/db/startup-progress.ts';

const samples: Array<{ phase: 'download' | 'open' | 'validate'; t: number; expect: number }> = [
  { phase: 'download', t: 0, expect: 0 },
  { phase: 'download', t: 1, expect: 85 },
  { phase: 'open', t: 0, expect: 85 },
  { phase: 'open', t: 1, expect: 95 },
  { phase: 'validate', t: 0, expect: 95 },
  { phase: 'validate', t: 1, expect: 100 },
];

let last = -1;
const unsub = subscribeGateProgress((p) => {
  last = p;
});

for (const { phase, t, expect } of samples) {
  reportGatePhase(phase, t);
  if (last !== expect) {
    throw new Error(`startup-progress-self-check: ${phase}@${t} → ${last}, expected ${expect}`);
  }
}

unsub();
console.log('startup-progress self-check ok');