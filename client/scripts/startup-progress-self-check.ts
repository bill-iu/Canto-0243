/** ADR-0032: gate progress weights + monotonic high-water */
import {
  reportGatePhase,
  resetGateProgress,
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

resetGateProgress();
for (const { phase, t, expect } of samples) {
  reportGatePhase(phase, t);
  if (last !== expect) {
    throw new Error(`startup-progress-self-check: ${phase}@${t} → ${last}, expected ${expect}`);
  }
}

// Monotonic: OPFS open@0.9 then init open@0.4 must not shrink ink.
resetGateProgress();
reportGatePhase('open', 0.9);
if (last !== 94) {
  throw new Error(`startup-progress-self-check: open@0.9 → ${last}, expected 94`);
}
reportGatePhase('open', 0.4);
if (last !== 94) {
  throw new Error(`startup-progress-self-check: regress open@0.4 → ${last}, expected 94`);
}
reportGatePhase('open', 1);
if (last !== 95) {
  throw new Error(`startup-progress-self-check: open@1 → ${last}, expected 95`);
}

// Degrade-style drop (download@1 after high open) stays at high-water.
resetGateProgress();
reportGatePhase('open', 0.9);
reportGatePhase('download', 1);
if (last !== 94) {
  throw new Error(`startup-progress-self-check: download after open → ${last}, expected 94`);
}

unsub();
console.log('startup-progress self-check ok');
