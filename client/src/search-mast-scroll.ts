/** Search header tracks the results scroller 1:1.
 *  Wide PWA: logo + title hide; the workbench chip and menu lift onto the tab row.
 *  Narrow PWA: logo hides, and the menu lifts onto the tab row. */

export const SEARCH_MAST_WIDE_MQ = '(min-width: 761px)';
export const SEARCH_MAST_SCROLLERS =
  '.search-results-scroll, .guide-quick__rows, .guide-quick__columns';

export function searchMastY(scrollTop: number, mastMax: number, reducedMotion: boolean): number {
  if (mastMax <= 0) return 0;
  const y = Math.max(0, scrollTop);
  if (reducedMotion) return y > 8 ? mastMax : 0;
  return Math.min(y, mastMax);
}

export function searchMastCollapsed(y: number, mastMax: number): boolean {
  return mastMax > 0 && y >= mastMax - 0.5;
}

/** Pixels to translate the menu up so its trigger center meets the tab center. */
export function searchMastLift(menuMid: number, tabMid: number): number {
  return Math.max(0, menuMid - tabMid);
}

export function searchMastSelfCheck(): void {
  if (searchMastY(-4, 80, false) !== 0) throw new Error('negative scroll clamps to 0');
  if (searchMastY(20, 80, false) !== 20) throw new Error('offset tracks scroll');
  if (searchMastY(200, 80, false) !== 80) throw new Error('offset stops at mast height');
  if (searchMastY(4, 80, true) !== 0 || searchMastY(9, 80, true) !== 80) {
    throw new Error('reduced motion snaps');
  }
  if (searchMastCollapsed(79, 80) || !searchMastCollapsed(80, 80)) {
    throw new Error('collapsed only at the end of the mast');
  }
  if (searchMastLift(100, 40) !== 60) throw new Error('lift is the gap up to the tab');
  if (searchMastLift(10, 40) !== 0) throw new Error('lift never pushes the menu down');
}

export function bindSearchMastScroll(appBar: HTMLElement, shell: HTMLElement): () => void {
  const header = appBar.closest<HTMLElement>('.app-header') ?? appBar;
  const track = appBar.querySelector<HTMLElement>('.header-mast__track');
  const wideMq = window.matchMedia(SEARCH_MAST_WIDE_MQ);
  const reduceMq = window.matchMedia('(prefers-reduced-motion: reduce)');
  let mastMax = 0;
  let lift = 0;
  let menuInset = 0;

  const menuEl = () => appBar.querySelector<HTMLElement>('.header-chrome__actions');
  const pills = () => header.querySelector<HTMLElement>('.query-tabs-bar');
  const narrowPwa = () => !wideMq.matches && Boolean(pills());

  const measure = () => {
    const menu = menuEl();
    const wide = wideMq.matches;
    if (wide) {
      mastMax = track?.offsetHeight ?? 0;
    } else {
      // SVG offsetHeight stays 0; the border box is what the row actually shows.
      const logo = appBar.querySelector<HTMLElement>('.brand-logo');
      const logoH = logo ? Math.round(logo.getBoundingClientRect().height) : 0;
      const menuH = menu?.offsetHeight ?? 0;
      mastMax = Math.max(logoH, menuH);
      appBar.style.setProperty('--mast-logo', `${logoH}px`);
    }
    appBar.style.setProperty('--mast-max', `${mastMax}px`);
    if (menu) {
      const corner = `${menu.offsetWidth}px`;
      appBar.style.setProperty('--mast-corner', corner);
      header.style.setProperty('--mast-corner', corner);
    }
    appBar.classList.add('is-mast-measured');
    header.classList.toggle('is-mast-narrow', !wide && Boolean(pills()));
    header.classList.toggle('is-mast-wide', wide && Boolean(pills()));
    lift = 0;
    menuInset = 0;
    const tab = header.querySelector<HTMLElement>('.query-tab-pill, .query-tab-add');
    if (menu && tab && (wide || narrowPwa())) {
      const trigger = menu.querySelector<HTMLElement>('.menu-trigger') ?? menu;
      const prev = menu.style.transform;
      menu.style.transform = 'none';
      void menu.offsetHeight;
      const tabBox = tab.getBoundingClientRect();
      const trigBox = trigger.getBoundingClientRect();
      menu.style.transform = prev;
      lift = searchMastLift(trigBox.top + trigBox.height / 2, tabBox.top + tabBox.height / 2);
      const pad = Number.parseFloat(getComputedStyle(header).paddingRight) || 0;
      menuInset = Math.max(0, header.getBoundingClientRect().right - pad - menu.getBoundingClientRect().right);
    }
  };

  const clearMotion = () => {
    appBar.style.setProperty('--mast-y', '0px');
    header.style.setProperty('--mast-lift', '0px');
    header.style.setProperty('--mast-reserve', '0px');
    appBar.classList.remove('is-mast-collapsed', 'is-mast-overlap');
    header.classList.remove('is-mast-collapsed', 'is-mast-narrow', 'is-mast-wide', 'is-mast-tab-reserve');
  };

  const apply = (scrollTop: number) => {
    const workbench = appBar.classList.contains('app-bar--workbench');
    const wide = wideMq.matches;
    if (workbench || (!wide && !narrowPwa())) {
      clearMotion();
      return;
    }
    const y = searchMastY(scrollTop, mastMax, reduceMq.matches);
    appBar.style.setProperty('--mast-y', `${y}px`);
    const collapsed = searchMastCollapsed(y, mastMax);
    appBar.classList.toggle('is-mast-collapsed', collapsed);
    header.classList.toggle('is-mast-collapsed', collapsed);
    const menu = menuEl();
    if (wide && !pills()) {
      const menuH = menu?.offsetHeight ?? 0;
      appBar.classList.toggle('is-mast-overlap', mastMax > 0 && mastMax - y < menuH);
      header.style.setProperty('--mast-lift', '0px');
      header.style.setProperty('--mast-reserve', '0px');
      header.classList.remove('is-mast-wide', 'is-mast-tab-reserve');
      if (menu) appBar.style.setProperty('--mast-corner', `${menu.offsetWidth}px`);
      return;
    }
    const progress = mastMax > 0 ? y / mastMax : 0;
    header.classList.toggle('is-mast-narrow', !wide);
    header.classList.toggle('is-mast-wide', wide);
    header.style.setProperty('--mast-lift', `${lift * progress}px`);
    appBar.classList.remove('is-mast-overlap');
    const corner = menu?.offsetWidth ?? 0;
    if (menu) {
      const cornerPx = `${corner}px`;
      appBar.style.setProperty('--mast-corner', cornerPx);
      header.style.setProperty('--mast-corner', cornerPx);
    }
    const reserve = progress > 0 ? (corner + menuInset + 8) * progress : 0;
    header.style.setProperty('--mast-reserve', `${reserve}px`);
    header.classList.toggle('is-mast-tab-reserve', reserve > 0);
  };

  const readScroll = () => {
    let top = 0;
    for (const node of shell.querySelectorAll<HTMLElement>(SEARCH_MAST_SCROLLERS)) {
      if (node.scrollTop > top) top = node.scrollTop;
    }
    apply(top);
  };

  const onScroll = (event: Event) => {
    const target = event.target;
    if (!(target instanceof Element) || !target.matches(SEARCH_MAST_SCROLLERS)) return;
    apply((target as HTMLElement).scrollTop);
  };

  const ro = new ResizeObserver(() => {
    measure();
    readScroll();
  });
  if (track) ro.observe(track);
  const logo = appBar.querySelector('.brand-logo');
  if (logo) ro.observe(logo);
  const menu = menuEl();
  if (menu) ro.observe(menu);
  measure();
  readScroll();
  shell.addEventListener('scroll', onScroll, { capture: true, passive: true });
  const onMq = () => {
    measure();
    readScroll();
  };
  wideMq.addEventListener('change', onMq);
  reduceMq.addEventListener('change', onMq);

  return () => {
    ro.disconnect();
    shell.removeEventListener('scroll', onScroll, true);
    wideMq.removeEventListener('change', onMq);
    reduceMq.removeEventListener('change', onMq);
    appBar.style.removeProperty('--mast-y');
    appBar.style.removeProperty('--mast-max');
    appBar.style.removeProperty('--mast-logo');
    appBar.style.removeProperty('--mast-corner');
    header.style.removeProperty('--mast-lift');
    header.style.removeProperty('--mast-reserve');
    header.style.removeProperty('--mast-corner');
    appBar.classList.remove('is-mast-measured', 'is-mast-collapsed', 'is-mast-overlap');
    header.classList.remove('is-mast-collapsed', 'is-mast-narrow', 'is-mast-wide', 'is-mast-tab-reserve');
  };
}
