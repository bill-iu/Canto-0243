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
  <svg viewBox="0 0 24 24" fill="none" {...S}>
    <path d="M12 10.4V20M12 10.4C12 8.15979 12 7.03969 11.564 6.18404C11.1805 5.43139 10.5686 4.81947 9.81596 4.43597C8.96031 4 7.84021 4 5.6 4H4.6C4.03995 4 3.75992 4 3.54601 4.10899C3.35785 4.20487 3.20487 4.35785 3.10899 4.54601C3 4.75992 3 5.03995 3 5.6V16.4C3 16.9601 3 17.2401 3.10899 17.454C3.20487 17.6422 3.35785 17.7951 3.54601 17.891C3.75992 18 4.03995 18 4.6 18H7.54668C8.08687 18 8.35696 18 8.61814 18.0466C8.84995 18.0879 9.0761 18.1563 9.29191 18.2506C9.53504 18.3567 9.75977 18.5065 10.2092 18.8062L12 20M12 10.4C12 8.15979 12 7.03969 12.436 6.18404C12.8195 5.43139 13.4314 4.81947 14.184 4.43597C15.0397 4 16.1598 4 18.4 4H19.4C19.9601 4 20.2401 4 20.454 4.10899C20.6422 4.20487 20.7951 4.35785 20.891 4.54601C21 4.75992 21 5.03995 21 5.6V16.4C21 16.9601 21 17.2401 20.891 17.454C20.7951 17.6422 20.6422 17.7951 20.454 17.891C20.2401 18 19.9601 18 19.4 18H16.4533C15.9131 18 15.643 18 15.3819 18.0466C15.15 18.0879 14.9239 18.1563 14.7081 18.2506C14.465 18.3567 14.2402 18.5065 13.7908 18.8062L12 20" />
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
