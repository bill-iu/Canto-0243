import { $, VIEW } from "./app-context.mjs";
import {
  activeTab, updateBrowserUrlFromActiveTab, scrollActiveTabIntoView,
} from "./tabs-core.mjs";
import { renderTabstrip } from "./tabs-ui.mjs";
import {
  shouldShowLoadMore, renderSearchResults, toggleLoadMoreButton, updateShuffleButton,
} from "./search-workbench.mjs";
import { applyRelationForm } from "./relation-form.mjs";

function syncViewPanels({ renderTabstrip: shouldRenderTabstrip = true } = {}) {
  const tab = activeTab();
  if (!tab) return;
  const isSearch = tab.view === VIEW.SEARCH;
  const isGuide = tab.view === VIEW.GUIDE;
  const isRelation = tab.view === VIEW.RELATION;
  $.searchView.hidden = !isSearch;
  $.guideView.hidden = !isGuide;
  $.relationView.hidden = !isRelation;
  $.searchView.classList.toggle("is-hidden", !isSearch);
  $.guideView.classList.toggle("is-hidden", !isGuide);
  $.relationView.classList.toggle("is-hidden", !isRelation);
  if (isSearch) {
    $.searchInput.value = tab.q || "";
    renderSearchResults(tab.results || [], tab.total);
    toggleLoadMoreButton(shouldShowLoadMore(tab));
    updateShuffleButton();
  } else if (isRelation) {
    applyRelationForm(tab.relation || {});
  }
  updateBrowserUrlFromActiveTab(true);
  if (shouldRenderTabstrip) renderTabstrip();
  else requestAnimationFrame(scrollActiveTabIntoView);
}
