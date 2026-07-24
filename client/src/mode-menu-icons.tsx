import type { FC } from 'react';

const S = { stroke: 'currentColor', strokeWidth: 1.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
const V = '0 0 16 16';

export const IconSearch: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <circle cx="6.5" cy="6.5" r="4.5" />
    <line x1="9.8" y1="9.8" x2="14" y2="14" />
  </svg>
);

export const IconPingze: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <text x="2" y="7" fontSize="8" fontWeight="700" fill="currentColor" stroke="none" fontFamily="sans-serif">P</text>
    <line x1="6" y1="1" x2="11" y2="15" />
    <text x="9" y="15" fontSize="8" fontWeight="700" fill="currentColor" stroke="none" fontFamily="sans-serif">Z</text>
  </svg>
);

export const IconSynonym: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <circle cx="8" cy="8" r="5" />
    <polyline points="5,5 3,8 5,11" />
    <polyline points="11,11 13,8 11,5" />
  </svg>
);

export const IconWorkbench: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <path d="M11 2l3 3-8 9-4 1 1-4z" />
    <line x1="10" y1="3" x2="13" y2="6" />
  </svg>
);

export const IconGuide: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <circle cx="8" cy="8" r="6" />
    <text x="8" y="11.5" fontSize="9" fontWeight="700" fill="currentColor" stroke="none" textAnchor="middle" fontFamily="sans-serif">?</text>
  </svg>
);

export const IconRelation: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <line x1="3" y1="8" x2="13" y2="8" />
    <line x1="8" y1="3" x2="8" y2="13" />
  </svg>
);

export const IconAbout: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <circle cx="8" cy="8" r="6" />
    <text x="8" y="11.5" fontSize="9" fontWeight="700" fill="currentColor" stroke="none" textAnchor="middle" fontFamily="sans-serif">i</text>
  </svg>
);

export const IconPower: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <path d="M8 2v6" />
    <path d="M3 6a6 6 0 1 0 10 0" />
  </svg>
);

export const IconLanguage: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <text x="8" y="7.5" fontSize="7" fontWeight="700" fill="currentColor" stroke="none" textAnchor="middle" fontFamily="sans-serif">A</text>
    <text x="8" y="14.5" fontSize="7" fontWeight="700" fill="currentColor" stroke="none" textAnchor="middle" fontFamily="sans-serif">中</text>
  </svg>
);

export const IconSun: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <circle cx="8" cy="8" r="3" />
    <line x1="8" y1="1" x2="8" y2="3" />
    <line x1="8" y1="13" x2="8" y2="15" />
    <line x1="1" y1="8" x2="3" y2="8" />
    <line x1="13" y1="8" x2="15" y2="8" />
    <line x1="3.5" y1="3.5" x2="5" y2="5" />
    <line x1="11" y1="11" x2="12.5" y2="12.5" />
    <line x1="3.5" y1="12.5" x2="5" y2="11" />
    <line x1="12.5" y1="3.5" x2="11" y2="5" />
  </svg>
);

export const IconMoon: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <path d="M12 8a6 6 0 0 1-6 6 6 6 0 0 1 0-12 6 6 0 0 0 6 6z" />
  </svg>
);
