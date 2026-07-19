/**
 * Narrow-header tagline fit: shrink font until it fits; hide if still overflow at min.
 * ponytail: pure planner for DOM loop + self-check; no framework.
 */

export const HEADER_TAGLINE_MIN_PX = 10;
export const HEADER_NARROW_MQ = '(max-width: 760px)';

export function nextTaglineFontSize(opts: {
  scrollWidth: number;
  clientWidth: number;
  fontSizePx: number;
  minPx?: number;
  stepPx?: number;
}): { fontSizePx: number; hide: boolean; done: boolean } {
  const minPx = opts.minPx ?? HEADER_TAGLINE_MIN_PX;
  const stepPx = opts.stepPx ?? 0.5;
  if (opts.clientWidth <= 0 || opts.scrollWidth <= opts.clientWidth + 0.5) {
    return { fontSizePx: opts.fontSizePx, hide: false, done: true };
  }
  if (opts.fontSizePx <= minPx) {
    return { fontSizePx: minPx, hide: true, done: true };
  }
  return {
    fontSizePx: Math.max(minPx, Math.round((opts.fontSizePx - stepPx) * 10) / 10),
    hide: false,
    done: false,
  };
}

/** Apply fit to a tagline element. Returns whether it is hidden. */
export function fitHeaderTaglineEl(
  el: HTMLElement,
  opts?: { minPx?: number; isNarrow?: boolean },
): boolean {
  const minPx = opts?.minPx ?? HEADER_TAGLINE_MIN_PX;
  const isNarrow = opts?.isNarrow ?? true;
  if (!isNarrow) {
    el.hidden = false;
    el.style.fontSize = '';
    return false;
  }
  el.hidden = false;
  el.style.fontSize = '';
  let fontSizePx = Number.parseFloat(getComputedStyle(el).fontSize) || 12;
  el.style.fontSize = `${fontSizePx}px`;
  for (let i = 0; i < 40; i++) {
    const step = nextTaglineFontSize({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      fontSizePx,
      minPx,
    });
    fontSizePx = step.fontSizePx;
    el.style.fontSize = `${fontSizePx}px`;
    if (step.hide) {
      el.hidden = true;
      el.style.fontSize = '';
      return true;
    }
    if (step.done) {
      el.hidden = false;
      return false;
    }
  }
  el.hidden = true;
  el.style.fontSize = '';
  return true;
}

export function headerTaglineFitSelfCheck(): void {
  const ok = nextTaglineFontSize({
    scrollWidth: 100,
    clientWidth: 100,
    fontSizePx: 12,
  });
  if (!ok.done || ok.hide) {
    throw new Error('headerTaglineFitSelfCheck: fitted text should be done');
  }
  const shrink = nextTaglineFontSize({
    scrollWidth: 200,
    clientWidth: 100,
    fontSizePx: 12,
  });
  if (shrink.done || shrink.fontSizePx >= 12) {
    throw new Error('headerTaglineFitSelfCheck: should shrink');
  }
  const hide = nextTaglineFontSize({
    scrollWidth: 200,
    clientWidth: 100,
    fontSizePx: 10,
    minPx: 10,
  });
  if (!hide.hide || !hide.done) {
    throw new Error('headerTaglineFitSelfCheck: min size should hide');
  }
}
