/** ponytail: batch window stays at 50 until scroll; no auto pump */
import {
  RESULT_RENDER_BATCH,
  expandRenderedCount,
  resetRenderedCount,
  isSentinelIntersecting,
} from "../infinite-results.mjs";

const tab = {};
resetRenderedCount(tab, 1200);
if (tab.renderedCount !== 50) throw new Error(`reset → ${tab.renderedCount}`);
expandRenderedCount(tab, 1200);
if (tab.renderedCount !== 100) throw new Error(`expand → ${tab.renderedCount}`);

const root = { getBoundingClientRect: () => ({ top: 0, left: 0, right: 400, bottom: 300 }) };
const sentinelBelow = {
  hidden: false,
  getBoundingClientRect: () => ({ top: 800, left: 0, right: 400, bottom: 820 }),
};
if (isSentinelIntersecting(root, sentinelBelow, 0)) {
  throw new Error("sentinel below fold should not intersect");
}

if (RESULT_RENDER_BATCH !== 50) throw new Error(`batch ${RESULT_RENDER_BATCH}`);
console.log("infinite-results-self-check ok");