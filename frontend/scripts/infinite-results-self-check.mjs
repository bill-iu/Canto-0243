/** ponytail: desktop infinite scroll — fetched page should render in full */
import { revealFetchedPage, RESULT_RENDER_BATCH } from "../infinite-results.mjs";

const tab = {};
for (const itemCount of [1200, 5501, 50, 100]) {
  revealFetchedPage(tab, itemCount);
  if (tab.renderedCount !== itemCount) {
    throw new Error(`revealFetchedPage(${itemCount}) → ${tab.renderedCount}`);
  }
}

if (RESULT_RENDER_BATCH !== 50) {
  throw new Error(`RESULT_RENDER_BATCH expected 50, got ${RESULT_RENDER_BATCH}`);
}

console.log("infinite-results-self-check ok");