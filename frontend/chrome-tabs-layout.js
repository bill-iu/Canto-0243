/**
 * Layout engine adapted from https://github.com/adamschwartz/chrome-tabs (MIT).
 * Prototype: no Draggabilly; positions tabs via injected CSS rules.
 */
(function (global) {
  const TAB_CONTENT_MARGIN = 9;
  const TAB_CONTENT_OVERLAP_DISTANCE = 1;
  const TAB_CONTENT_MIN_WIDTH = 24;
  const TAB_CONTENT_MAX_WIDTH = 256;
  const ADD_TAB_WIDTH = 52;
  const ADD_TAB_GAP = 0;
  const TAB_SIZE_SMALL = 96;
  const TAB_SIZE_SMALLER = 70;
  const TAB_SIZE_MINI = 56;

  const TAB_GEOMETRY_SVG = `
    <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <svg width="52%" height="100%">
        <use xlink:href="#query-tab-geometry" width="214" height="36" class="chrome-tab-geometry"/>
      </svg>
      <g transform="scale(-1, 1)">
        <svg width="52%" height="100%" x="-100%" y="0">
          <use xlink:href="#query-tab-geometry" width="214" height="36" class="chrome-tab-geometry"/>
        </svg>
      </g>
    </svg>`;

  let instanceId = 0;

  function tabTemplate() {
    return `
      <div class="chrome-tab">
        <div class="chrome-tab-dividers"></div>
        <div class="chrome-tab-background">${TAB_GEOMETRY_SVG}</div>
        <div class="chrome-tab-content">
          <div class="chrome-tab-favicon" hidden></div>
          <div class="chrome-tab-title"></div>
          <div class="chrome-tab-drag-handle" data-tab-select></div>
          <button type="button" class="chrome-tab-close" aria-label="關閉分頁"></button>
        </div>
      </div>`;
  }

  class QueryChromeTabsLayout {
    constructor(rootEl) {
      this.rootEl = rootEl;
      this.instanceId = instanceId++;
      this.rootEl.setAttribute("data-chrome-tabs-instance-id", String(this.instanceId));
      this.rootEl.style.setProperty("--tab-content-margin", `${TAB_CONTENT_MARGIN}px`);
      this.contentEl = this.rootEl.querySelector(".chrome-tabs-content");
      this.styleEl = this.rootEl.querySelector(".chrome-tabs-layout-style");
      if (!this.styleEl) {
        this.styleEl = document.createElement("style");
        this.styleEl.className = "chrome-tabs-layout-style";
        this.rootEl.appendChild(this.styleEl);
      }
      window.addEventListener("resize", () => this.layout());
    }

    get tabEls() {
      return Array.from(this.contentEl.querySelectorAll(".chrome-tab"));
    }

    get normalTabEls() {
      return this.tabEls.filter((el) => !el.classList.contains("chrome-tab-add"));
    }

    get addTabEl() {
      return this.contentEl.querySelector(".chrome-tab-add");
    }

    get tabContentWidths() {
      const numberOfTabs = this.normalTabEls.length;
      if (!numberOfTabs) return [];
      const tabsContentWidth = Math.max(0, this.contentEl.clientWidth - (ADD_TAB_WIDTH + ADD_TAB_GAP));
      const tabsCumulativeOverlappedWidth = (numberOfTabs - 1) * TAB_CONTENT_OVERLAP_DISTANCE;
      const maxTotalIfMax =
        numberOfTabs * TAB_CONTENT_MAX_WIDTH + 2 * TAB_CONTENT_MARGIN - tabsCumulativeOverlappedWidth;
      if (tabsContentWidth >= maxTotalIfMax) {
        return new Array(numberOfTabs).fill(TAB_CONTENT_MAX_WIDTH);
      }
      const targetWidth =
        (tabsContentWidth - 2 * TAB_CONTENT_MARGIN + tabsCumulativeOverlappedWidth) / numberOfTabs;
      const clampedTargetWidth = Math.max(
        TAB_CONTENT_MIN_WIDTH,
        Math.min(TAB_CONTENT_MAX_WIDTH, targetWidth)
      );
      const floored = Math.floor(clampedTargetWidth);
      const totalUsingTarget =
        floored * numberOfTabs + 2 * TAB_CONTENT_MARGIN - tabsCumulativeOverlappedWidth;
      let extra = tabsContentWidth - totalUsingTarget;
      const widths = [];
      for (let i = 0; i < numberOfTabs; i += 1) {
        const bump = floored < TAB_CONTENT_MAX_WIDTH && extra > 0 ? 1 : 0;
        widths.push(floored + bump);
        if (extra > 0) extra -= 1;
      }
      return widths;
    }

    get tabContentPositions() {
      const positions = [];
      const widths = this.tabContentWidths;
      let position = TAB_CONTENT_MARGIN;
      widths.forEach((width, i) => {
        positions.push(position - i * TAB_CONTENT_OVERLAP_DISTANCE);
        position += width;
      });
      return positions;
    }

    get tabPositions() {
      return this.tabContentPositions.map((p) => p - TAB_CONTENT_MARGIN);
    }

    layout() {
      const widths = this.tabContentWidths;
      const tabs = this.normalTabEls;
      tabs.forEach((tabEl, i) => {
        const contentWidth = widths[i] || TAB_CONTENT_MAX_WIDTH;
        tabEl.style.width = `${contentWidth + 2 * TAB_CONTENT_MARGIN}px`;
        tabEl.removeAttribute("is-small");
        tabEl.removeAttribute("is-smaller");
        tabEl.removeAttribute("is-mini");
        if (contentWidth < TAB_SIZE_SMALL) tabEl.setAttribute("is-small", "");
        if (contentWidth < TAB_SIZE_SMALLER) tabEl.setAttribute("is-smaller", "");
        if (contentWidth < TAB_SIZE_MINI) tabEl.setAttribute("is-mini", "");
      });
      const positions = this.tabPositions;
      tabs.forEach((tabEl, i) => {
        tabEl.style.transform = `translate3d(${positions[i] || 0}px,0,0)`;
      });

      const addEl = this.addTabEl;
      if (addEl) {
        const lastTabIdx = tabs.length - 1;
        const lastPos = positions[lastTabIdx] || TAB_CONTENT_MARGIN;
        const lastWidth = parseFloat(tabs[lastTabIdx]?.style.width || "0") || 0;
        const addPos = Math.max(TAB_CONTENT_MARGIN, lastPos + lastWidth - TAB_CONTENT_OVERLAP_DISTANCE + ADD_TAB_GAP);
        addEl.style.width = `${ADD_TAB_WIDTH}px`;
        addEl.style.transform = `translate3d(${addPos}px,0,0)`;
      }
    }

    createTabEl() {
      const wrap = document.createElement("div");
      wrap.innerHTML = tabTemplate().trim();
      return wrap.firstElementChild;
    }
  }

  global.QueryChromeTabsLayout = QueryChromeTabsLayout;
})(window);
