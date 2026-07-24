export const MODE_MENU_MIN_SCALE = 0.75;
export const MODE_MENU_GAP_PX = 12;

export function fitModeMenuScale(opts: {
  naturalHeight: number;
  availableHeight: number;
  minScale?: number;
  maxScale?: number;
}): { scale: number; scroll: boolean } {
  const minScale = opts.minScale ?? MODE_MENU_MIN_SCALE;
  const maxScale = opts.maxScale ?? 1;
  if (opts.naturalHeight <= opts.availableHeight + 0.5) {
    return { scale: maxScale, scroll: false };
  }
  const ratio = opts.availableHeight / opts.naturalHeight;
  const scale = Math.max(ratio, minScale);
  const capped = Math.min(scale, maxScale);
  const scaledHeight = opts.naturalHeight * capped;
  const scroll = scaledHeight > opts.availableHeight + 0.5;
  return { scale: capped, scroll };
}

export function fitModeMenuScaleSelfCheck(): void {
  const fits = fitModeMenuScale({ naturalHeight: 400, availableHeight: 600 });
  if (fits.scale !== 1 || fits.scroll !== false) {
    throw new Error('fitModeMenuScale: should fit without scale');
  }
  const shrinks = fitModeMenuScale({ naturalHeight: 500, availableHeight: 400 });
  if (Math.abs(shrinks.scale - 0.8) > 0.01 || shrinks.scroll !== false) {
    throw new Error('fitModeMenuScale: should scale down');
  }
  const floors = fitModeMenuScale({ naturalHeight: 400, availableHeight: 200 });
  if (Math.abs(floors.scale - 0.75) > 0.01 || floors.scroll !== true) {
    throw new Error('fitModeMenuScale: should floor at 0.75 and scroll');
  }
  const exact = fitModeMenuScale({ naturalHeight: 400, availableHeight: 300 });
  if (Math.abs(exact.scale - 0.75) > 0.01 || exact.scroll !== false) {
    throw new Error('fitModeMenuScale: floor without scroll at exact fit');
  }
  const narrowCapped = fitModeMenuScale({ naturalHeight: 300, availableHeight: 500, maxScale: 0.75 });
  if (Math.abs(narrowCapped.scale - 0.75) > 0.01 || narrowCapped.scroll !== false) {
    throw new Error('fitModeMenuScale: narrow maxScale cap');
  }
  const narrowOverflow = fitModeMenuScale({ naturalHeight: 600, availableHeight: 400, maxScale: 0.75 });
  if (Math.abs(narrowOverflow.scale - 0.75) > 0.01 || narrowOverflow.scroll !== true) {
    throw new Error('fitModeMenuScale: narrow overflow with scroll');
  }
}
