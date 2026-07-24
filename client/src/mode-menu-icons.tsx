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
    <text x="2" y="6" fontSize="8" fontWeight="700" fill="currentColor" stroke="none" fontFamily="sans-serif">P</text>
    <line x1="4" y1="11" x2="11" y2="4" />
    <text x="9" y="14" fontSize="8" fontWeight="700" fill="currentColor" stroke="none" fontFamily="sans-serif">Z</text>
  </svg>
);

export const IconSynonym: FC = () => (
  <svg viewBox={V} fill="none" {...S}>
    <path d="M3 6 C3 2 13 2 13 6" />
    <polyline points="13,6 10,4 13,6 10,8" />
    <path d="M13 10 C13 14 3 14 3 10" />
    <polyline points="3,10 6,12 3,10 6,8" />
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
    <path d="M3 4 Q3 2 8 3 V13 Q3 14 3 15 Z" />
    <path d="M13 4 Q13 2 8 3 V13 Q13 14 13 15 Z" />
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
    <circle cx="8" cy="4.5" r="1.2" fill="currentColor" stroke="none" />
    <line x1="8" y1="6.5" x2="8" y2="11" />
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
    <path d="M10 4 a5 5 0 1 0 0 8 a4 4 0 0 1 0-8z" />
  </svg>
);
