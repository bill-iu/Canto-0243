/** Tab chrome geometry markup — single source for ESM + classic scripts. */
(function (g) {
  g.TAB_GEOMETRY_SVG = `
  <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <svg width="52%" height="100%"><use xlink:href="#query-tab-geometry" width="214" height="36" class="chrome-tab-geometry"/></svg>
    <g transform="scale(-1, 1)"><svg width="52%" height="100%" x="-100%" y="0"><use xlink:href="#query-tab-geometry" width="214" height="36" class="chrome-tab-geometry"/></svg></g>
  </svg>`;
})(globalThis);
