/** ponytail: IO pump + batch window — expand while sentinel visible */
import {
  RESULT_RENDER_BATCH,
  expandRenderedCount,
  resetRenderedCount,
  isSentinelIntersecting,
  scheduleScrollPump,
  SCROLL_PUMP_MAX_STEPS,
} from "../infinite-results.mjs";

const tab = {};
resetRenderedCount(tab, 1200);
if (tab.renderedCount !== 50) throw new Error(`reset → ${tab.renderedCount}`);
expandRenderedCount(tab, 1200);
if (tab.renderedCount !== 100) throw new Error(`expand → ${tab.renderedCount}`);

let pumpCalls = 0;
const root = { getBoundingClientRect: () => ({ top: 0, left: 0, right: 400, bottom: 600 }) };
const sentinel = {
  hidden: false,
  getBoundingClientRect: () => ({ top: 500, left: 0, right: 400, bottom: 520 }),
};
if (!isSentinelIntersecting(root, sentinel)) throw new Error("sentinel should intersect");

scheduleScrollPump({
  root,
  sentinel,
  onStep: () => {
    pumpCalls += 1;
    expandRenderedCount(tab, 1200);
  },
  maxSteps: SCROLL_PUMP_MAX_STEPS,
});

await new Promise((r) => setTimeout(r, 50));
if (pumpCalls < 2) throw new Error(`pump expected ≥2 steps, got ${pumpCalls}`);
if (tab.renderedCount < 150) throw new Error(`pump expand → ${tab.renderedCount}`);
if (RESULT_RENDER_BATCH !== 50) throw new Error(`batch ${RESULT_RENDER_BATCH}`);
console.log("infinite-results-self-check ok");