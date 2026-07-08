import { useEffect, useId, useRef, useState } from 'react';

import { getModeMeta, modeHelp, modeMetaFor, uiModeToUrlMode, type UiMode } from './mode-meta';

const MODE_OPTIONS: Array<{ uiMode: UiMode; key: string }> = [
  { uiMode: '0243', key: '0243' },
  { uiMode: '02493', key: '02493' },
  { uiMode: '394052', key: '394052' },
  { uiMode: 'synonym', key: '~ / !' },
];

export interface ModeMenuProps {
  mode: UiMode;
  disabled?: boolean;
  onModeChange: (mode: UiMode) => void;
  onOpenGuide: () => void;
  onOpenAbout: () => void;
  theme?: 'light' | 'dark';
  lang?: 'zh' | 'en';
  onThemeChange?: (theme: 'light' | 'dark') => void;
  onLangChange?: (lang: 'zh' | 'en') => void;
}

export function ModeMenu({
  mode,
  disabled = false,
  onModeChange,
  onOpenGuide,
  onOpenAbout,
  theme = 'light',
  lang = 'zh',
  onThemeChange,
  onLangChange,
}: ModeMenuProps) {
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const meta = modeMetaFor(mode, lang);
  const urlMode = uiModeToUrlMode(mode);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const close = () => setOpen(false);

  const pickMode = (next: UiMode) => {
    onModeChange(next);
    close();
  };

  return (
    <div className="app-actions mode-menu-root" ref={rootRef}>
      <button
        type="button"
        className="menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="mode-trigger-text">
          <span className="mode-trigger-primary">{meta.title}</span>
          <span className="mode-trigger-note">{meta.note}</span>
        </span>
        <span className="menu-chevron" aria-hidden="true">
          ▾
        </span>
      </button>

      <div
        id={menuId}
        className={`mode-menu${open ? ' is-open' : ''}`}
        role="menu"
        hidden={!open}
      >
        <div className="menu-group" role="group" aria-label={lang === 'zh' ? '0243搜尋模式' : '0243 Search Modes'}>
          <p className="menu-label">{lang === 'zh' ? '0243搜尋模式' : '0243 Search Modes'}</p>
          {MODE_OPTIONS.map((option) => {
            const optionMeta = getModeMeta(uiModeToUrlMode(option.uiMode), lang);
            const checked = uiModeToUrlMode(option.uiMode) === urlMode;
            return (
              <button
                key={option.uiMode}
                type="button"
                className="mode-option"
                role="menuitemradio"
                aria-checked={checked}
                disabled={disabled}
                onClick={() => pickMode(option.uiMode)}
              >
                <span>
                  <span className="mode-name">
                    {optionMeta.title}
                    <span className="mode-note">{optionMeta.note}</span>
                  </span>
                  <span className="mode-help">{modeHelp(option.uiMode, lang)}</span>
                </span>
                <span className="mode-key">{option.key}</span>
              </button>
            );
          })}
        </div>
        <div className="menu-group" role="group" aria-label={lang === 'zh' ? '工具' : 'Tools'}>
          <p className="menu-label">{lang === 'zh' ? '工具' : 'Tools'}</p>
          <button
            type="button"
            className="mode-option"
            role="menuitem"
            onClick={() => {
              onOpenGuide();
              close();
            }}
          >
            <span>
              <span className="mode-name">{lang === 'zh' ? '搜尋教學' : 'Search Guide'}</span>
              <span className="mode-help">{lang === 'zh' ? '完整語法與例子' : 'Full syntax & examples'}</span>
            </span>
            <span className="mode-key">?</span>
          </button>
          <button
            type="button"
            className="mode-option"
            role="menuitem"
            onClick={() => {
              onOpenAbout();
              close();
            }}
          >
            <span>
              <span className="mode-name">{lang === 'zh' ? '關於' : 'About'}</span>
              <span className="mode-help">{lang === 'zh' ? '授權、致謝與回報' : 'License, credits & feedback'}</span>
            </span>
            <span className="mode-key">i</span>
          </button>
        </div>

        {/* Compact switches row inside dropdown: theme icon + single lang toggle (side-by-side to shorten menu) */}
        <div className="menu-group" role="group" aria-label={lang === 'zh' ? '顯示' : 'Display'}>
          <p className="menu-label">{lang === 'zh' ? '顯示' : 'Display'}</p>
          <div className="menu-switches">
            <button
              type="button"
              className="mode-option mode-switch"
              onClick={() => {
                onThemeChange?.(theme === 'dark' ? 'light' : 'dark');
                close();
              }}
              aria-label={lang === 'zh' ? '切換主題' : 'Toggle theme'}
            >
              <span aria-hidden="true">{theme === 'dark' ? '🌙' : '☀️'}</span>
            </button>
            <button
              type="button"
              className="mode-option mode-switch"
              onClick={() => {
                onLangChange?.(lang === 'zh' ? 'en' : 'zh');
                close();
              }}
              aria-label={lang === 'zh' ? '切換語言' : 'Toggle language'}
            >
              <span>{lang === 'zh' ? '中 / EN' : 'EN / 中'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export { modeHelp };

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p6-mode-menu-self-check.ts` */
export function modeMenuSelfCheck(): void {
  if (MODE_OPTIONS.length !== 4) {
    throw new Error('modeMenuSelfCheck: mode options');
  }
  if (modeHelp('394052', 'zh') !== '394052 矩陣碼（三／五聲分明）') {
    throw new Error('modeMenuSelfCheck: m3 help');
  }
  if (modeHelp('synonym', 'zh') !== '近義、反義與語意相關') {
    throw new Error('modeMenuSelfCheck: syn help');
  }
  if (modeHelp('0243', 'en') !== 'Common 0243 codes & mixed queries') {
    throw new Error('modeMenuSelfCheck: en m1 help');
  }
}
