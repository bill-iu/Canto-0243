const LIGHT_INK = '#9F1239';
const DARK_INK = '#FB7185';
const GATE_INK_CLIP_MAX = 148;

export interface BrandLogoProps {
  className?: string;
  /** Gate overlay uses animated ink clip. */
  variant?: 'header' | 'gate';
  inkProgress?: number;
  /** Theme for logo colors (light uses original dark text + #9F1239 ink; dark uses light text + #FB7185 ink) */
  theme?: 'light' | 'dark';
}

function getBrandIds(theme?: 'light' | 'dark') {
  let resolved: 'light' | 'dark' = theme || 'light';
  if (!theme && typeof document !== 'undefined') {
    resolved = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
  }
  const isDark = resolved === 'dark';
  return {
    wordmark: isDark ? '#brand-wordmark-dark' : '#brand-wordmark',
    blob: isDark ? '#brand-ink-blob-dark' : '#brand-ink-blob',
    flicks: isDark ? '#brand-ink-flicks-dark' : '#brand-ink-flicks',
    ink: isDark ? DARK_INK : LIGHT_INK,
  };
}

export function BrandLogo({ className = 'brand-logo', variant = 'header', inkProgress = 1, theme = 'light' }: BrandLogoProps) {
  const { wordmark, blob, flicks, ink } = getBrandIds(theme);

  if (variant === 'gate') {
    const w = (Math.max(0, Math.min(1, inkProgress)) * GATE_INK_CLIP_MAX).toFixed(1);
    return (
      <svg
        className={`${className} brand-logo--gate`}
        xmlns="http://www.w3.org/2000/svg"
        width="148"
        height="72"
        viewBox="0 0 148 72"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <clipPath id="gate-ink-clip">
            <rect className="gate-ink-clip-rect" x="0" y="0" width={w} height="72" />
          </clipPath>
        </defs>
        <use href={wordmark} />
        <g className="gate-ink-track" aria-hidden="true">
          <use href={blob} fill={ink} filter="url(#brush-roughen-brand)" />
          <use href={flicks} filter="url(#brush-roughen-brand)" />
        </g>
        <g className="gate-ink-fill" clipPath="url(#gate-ink-clip)" aria-hidden="true">
          <use href={blob} fill={ink} filter="url(#brush-roughen-brand)" />
          <use href={flicks} filter="url(#brush-roughen-brand)" />
        </g>
      </svg>
    );
  }

  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="200"
      height="72"
      viewBox="0 0 200 72"
      aria-hidden="true"
      focusable="false"
    >
      <use href={wordmark} />
      <g aria-hidden="true">
        <use href={blob} fill={ink} filter="url(#brush-roughen-brand)" />
        <use href={flicks} filter="url(#brush-roughen-brand)" />
      </g>
    </svg>
  );
}

export function GateInkMeter({ inkProgress, theme = 'light' }: { inkProgress: number; theme?: 'light' | 'dark' }) {
  const { blob, flicks, ink } = getBrandIds(theme);
  const w = (Math.max(0, Math.min(1, inkProgress)) * GATE_INK_CLIP_MAX).toFixed(1);
  return (
    <svg
      className="gate-ink-meter"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 38 200 34"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <clipPath id="gate-ink-clip-mini">
          <rect className="gate-ink-clip-rect" x="0" y="38" width={w} height="34" />
        </clipPath>
      </defs>
      <g className="gate-ink-track" aria-hidden="true">
        <use href={blob} fill={ink} filter="url(#brush-roughen-brand)" />
        <use href={flicks} filter="url(#brush-roughen-brand)" />
      </g>
      <g className="gate-ink-fill" clipPath="url(#gate-ink-clip-mini)" aria-hidden="true">
        <use href={blob} fill={ink} filter="url(#brush-roughen-brand)" />
        <use href={flicks} filter="url(#brush-roughen-brand)" />
      </g>
    </svg>
  );
}
