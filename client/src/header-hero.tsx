import { useLayoutEffect, useRef } from 'react';

import {
  HEADER_NARROW_MQ,
  fitHeaderTaglineEl,
} from './header-hero-tagline-fit.ts';

export interface HeaderHeroProps {
  lang: 'zh' | 'en';
}

export function HeaderHero({ lang }: HeaderHeroProps) {
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
      <p className="header-hero__title">{lang === 'en' ? 'WRITE·RIGHT·RHYME' : 'ONE·搵·韻'}</p>
      <p className="header-hero__tagline" ref={taglineRef}>
        {lang === 'en'
          ? 'Meter / sound match / rhyme / near-antonyms — find in one step.'
          : '格律／協音／押韻／近反義，一步搵到。'}
      </p>
    </div>
  );
}
