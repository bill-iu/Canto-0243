import { $, VIEW, shell } from "./app-context.mjs";
import { activeTab, scrollActiveTabIntoView } from "./tabs-core.mjs";
import { renderTabstrip } from "./tabs-ui.mjs";
import {
  shouldShowLoadMore, renderSearchResults, toggleLoadMoreButton, updateShuffleButton,
} from "./search-workbench.mjs";
import { applyRelationForm } from "./relation-form.mjs";
import { mountCorrectionsPanel } from "./lexicon-corrections.mjs";
import { clearQueryExplain, refreshQueryExplain } from "./query-explain.mjs";

function syncViewPanels({ renderTabstrip: shouldRenderTabstrip = true } = {}) {
  const tab = activeTab();
  if (!tab) return;
  const isSearch = tab.view === VIEW.SEARCH;
  const isGuide = tab.view === VIEW.GUIDE;
  const isRelation = tab.view === VIEW.RELATION;
  const isCorrections = tab.view === VIEW.CORRECTIONS;
  $.searchView.hidden = !isSearch;
  $.guideView.hidden = !isGuide;
  $.relationView.hidden = !isRelation;
  $.correctionsView.hidden = !isCorrections;
  $.searchView.classList.toggle("is-hidden", !isSearch);
  $.guideView.classList.toggle("is-hidden", !isGuide);
  $.relationView.classList.toggle("is-hidden", !isRelation);
  $.correctionsView.classList.toggle("is-hidden", !isCorrections);
  if (isSearch) {
    $.searchInput.value = tab.q || "";
    renderSearchResults(tab.results || [], tab.total);
    toggleLoadMoreButton(shouldShowLoadMore(tab));
    updateShuffleButton();
    refreshQueryExplain(tab.q || "");
  } else {
    clearQueryExplain();
  }
  if (isRelation) {
    applyRelationForm(tab.relation || {});
  } else if (isCorrections) {
    mountCorrectionsPanel(tab);
  }
  if (shouldRenderTabstrip) renderTabstrip();
  else requestAnimationFrame(scrollActiveTabIntoView);
}

export { syncViewPanels };
