const INK = '#9F1239';
const GATE_INK_CLIP_MAX = 200;

export interface BrandLogoProps {
  className?: string;
  /** Gate overlay uses animated ink clip. */
  variant?: 'header' | 'gate';
  inkProgress?: number;
}

export function BrandLogo({ className = 'brand-logo', variant = 'header', inkProgress = 1 }: BrandLogoProps) {
  if (variant === 'gate') {
    const w = (Math.max(0, Math.min(1, inkProgress)) * GATE_INK_CLIP_MAX).toFixed(1);
    return (
      <svg
        className={`${className} brand-logo--gate`}
        xmlns="http://www.w3.org/2000/svg"
        width="200"
        height="72"
        viewBox="0 0 200 72"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <clipPath id="gate-ink-clip">
            <rect className="gate-ink-clip-rect" x="0" y="0" width={w} height="72" />
          </clipPath>
        </defs>
        <use href="#brand-wordmark" />
        <g className="gate-ink-track" aria-hidden="true">
          <use href="#brand-ink-blob" fill={INK} filter="url(#brush-roughen-brand)" />
          <use href="#brand-ink-flicks" filter="url(#brush-roughen-brand)" />
        </g>
        <g className="gate-ink-fill" clipPath="url(#gate-ink-clip)" aria-hidden="true">
          <use href="#brand-ink-blob" fill={INK} filter="url(#brush-roughen-brand)" />
          <use href="#brand-ink-flicks" filter="url(#brush-roughen-brand)" />
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
      <use href="#brand-wordmark" />
      <g aria-hidden="true">
        <use href="#brand-ink-blob" fill={INK} filter="url(#brush-roughen-brand)" />
        <use href="#brand-ink-flicks" filter="url(#brush-roughen-brand)" />
      </g>
    </svg>
  );
}

export function GateInkMeter({ inkProgress }: { inkProgress: number }) {
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
        <use href="#brand-ink-blob" fill={INK} filter="url(#brush-roughen-brand)" />
        <use href="#brand-ink-flicks" filter="url(#brush-roughen-brand)" />
      </g>
      <g className="gate-ink-fill" clipPath="url(#gate-ink-clip-mini)" aria-hidden="true">
        <use href="#brand-ink-blob" fill={INK} filter="url(#brush-roughen-brand)" />
        <use href="#brand-ink-flicks" filter="url(#brush-roughen-brand)" />
      </g>
    </svg>
  );
}
