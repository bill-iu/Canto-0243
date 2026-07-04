/** Shared SVG defs for Canto-0243 wordmark + ink (Portable parity). */
export function BrandSvgDefs() {
  return (
    <svg
      className="svg-defs"
      aria-hidden="true"
      width="0"
      height="0"
      style={{ position: 'absolute', overflow: 'hidden' }}
      focusable="false"
    >
      <defs>
        <filter id="brush-roughen-brand" x="-8%" y="-120%" width="116%" height="340%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.042 0.38"
            numOctaves={4}
            seed={7}
            result="turb"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="turb"
            scale={2.4}
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
        <symbol id="brand-wordmark" viewBox="0 0 200 72" overflow="visible">
          <text x="4" y="50" fontFamily="'Noto Serif TC', serif" fontSize="44" fontWeight="900" fill="#1C1917">
            粵
          </text>
          <text
            x="62"
            y="28"
            fontFamily="'Noto Serif TC', serif"
            fontSize="12"
            fontWeight="900"
            fill="#9F1239"
            letterSpacing="2.2"
          >
            CANTO
          </text>
          <text
            x="62"
            y="48"
            fontFamily="'JetBrains Mono', ui-monospace, monospace"
            fontSize="15"
            fontWeight="600"
            fill="#1C1917"
            letterSpacing="1"
          >
            0243
          </text>
        </symbol>
        <symbol id="brand-ink-blob" viewBox="0 0 200 72" overflow="visible">
          <path d="M4 55.5 C14 54.9 24 55.1 34 55.7 C44 56.3 52 56.7 60 56.5 C68 57.9 76 58.5 84 57.3 C92 55.2 98 52.8 104 51.2 C106.5 50.4 110 49.6 114 48.8 C118 47.6 122 47.2 126 46.8 C128 46.5 130 46.2 132 45.9 C133.5 45.6 134.5 45.4 135 45.2 L135.1 45.8 L134.6 46.3 L133.8 46.8 L132.6 47.3 L130.8 47.8 L128.5 48.2 C96 55.3 80 60.5 62 61.8 C46 62.3 30 60.3 18 57.3 C10 55.3 5 53.5 4 55.5 Z" />
        </symbol>
        <symbol id="brand-ink-flicks" viewBox="0 0 200 72" overflow="visible">
          <path d="M133.5 47.0 L135.0 45.5" stroke="#9F1239" strokeWidth="0.9" strokeLinecap="round" />
          <path d="M132.2 48.4 L133.6 49.2" stroke="#9F1239" strokeWidth="0.65" strokeLinecap="round" />
          <path d="M134.2 46.2 L135.2 44.9" stroke="#9F1239" strokeWidth="0.5" strokeLinecap="round" />
          <path d="M132.8 47.6 L134.0 48.4" stroke="#9F1239" strokeWidth="0.4" strokeLinecap="round" />
          <path d="M134.0 46.6 L135.0 45.8" stroke="#9F1239" strokeWidth="0.3" strokeLinecap="round" />
        </symbol>
      </defs>
    </svg>
  );
}
