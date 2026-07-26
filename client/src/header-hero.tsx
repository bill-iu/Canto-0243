import { useLayoutEffect, useRef } from 'react';

import {
  HEADER_NARROW_MQ,
  fitHeaderTaglineEl,
} from './header-hero-tagline-fit.ts';
import { getHeaderCopy } from '../../shared/header-i18n.mjs';

export interface HeaderHeroProps {
  lang: 'zh' | 'zh-Hans' | 'en';
}

export function HeaderHero({ lang }: HeaderHeroProps) {
  const copy = getHeaderCopy(lang);
  const rootRef = useRef<HTMLDivElement>(null);
  const taglineRef = useRef<HTMLParagraphElement>(null);

  useLayoutEffect(() => {
    const root = rootRef.current;
    const tagline = taglineRef.current;
    if (!root || !tagline) {
      return;
    }

    const run = () => {
      const narrow = window.matchMedia(HEADER_NARROW_MQ).matches;
      fitHeaderTaglineEl(tagline, { isNarrow: narrow });
    };

    run();
    const ro = new ResizeObserver(run);
    ro.observe(root);
    const mq = window.matchMedia(HEADER_NARROW_MQ);
    mq.addEventListener('change', run);
    let cancelled = false;
    void document.fonts.ready.then(() => {
      if (!cancelled) {
        run();
      }
    });
    return () => {
      cancelled = true;
      ro.disconnect();
      mq.removeEventListener('change', run);
    };
  }, [lang]);

  return (
    <div className="header-hero" aria-hidden="true" ref={rootRef}>
      <p className="header-hero__title">{copy.title}</p>
      <p className="header-hero__tagline" ref={taglineRef}>
        {copy.tagline}
      </p>
    </div>
  );
}
