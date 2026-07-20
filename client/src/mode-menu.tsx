import { useEffect, useId, useRef, useState } from 'react';

import { getModeMeta, modeHelp, modeMetaFor, type UiMode } from './mode-meta';
import { searchFamilyForUiMode } from '../../contracts/search-mode-manifest.mjs';
import { MODE_OPTIONS } from './mode-menu-logic.ts';

export interface ModeMenuProps {
  mode: UiMode;
  disabled?: boolean;
  onModeChange: (family: 'basic' | 'pingze' | 'synonym') => void;
  onOpenGuide: () => void;
  onOpenAbout: () => void;
  onOpenWorkbench?: () => void;
  /** Portable host only — 關係補錄 */
  onOpenRelation?: () => void;
  /** Portable host only — 退出本機服務 */
  onExitPortable?: () => void;
  theme?: 'light' | 'dark';
  lang?: 'zh' | 'en';
  onThemeChange?: (theme: 'light' | 'dark') => void;
  onLangChange?: (lang: 'zh' | 'en') => void;
  lexiconVersion?: string;
  showOpfsBackend?: boolean;
}

export function ModeMenu({
  mode,
  disabled = false,
  onModeChange,
  onOpenGuide,
  onOpenAbout,
  onOpenWorkbench,
  onOpenRelation,
  onExitPortable,
  theme = 'light',
  lang = 'zh',
  onThemeChange,
  onLangChange,
  lexiconVersion,
  showOpfsBackend = false,
}: ModeMenuProps) {
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const meta = modeMetaFor(mode, lang);
  const family = searchFamilyForUiMode(mode);

  // ponytail: mirror entry-detail first-tap-closes — swallow outside click so list picks don't fire
  useEffect(() => {
    if (!open) return;
    let suppressClick = false;
    const outside = (target: EventTarget | null) =>
      !rootRef.current?.contains(target as Node);

    const onPointerDown = (event: PointerEvent) => {
      if (!outside(event.target)) return;
      suppressClick = true;
      setOpen(false);
    };
    const onClickCapture = (event: MouseEvent) => {
      if (!suppressClick) return;
      if (!outside(event.target)) {
        suppressClick = false;
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      suppressClick = false;
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('pointerdown', onPointerDown, true);
    document.addEventListener('click', onClickCapture, true);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown, true);
      document.removeEventListener('click', onClickCapture, true);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const close = () => setOpen(false);

  const pickMode = (next: 'basic' | 'pingze' | 'synonym') => {
    onModeChange(next);
    close();
  };

  const metaLabel =
    lexiconVersion != null
      ? `${lang === 'en' ? 'Lexicon version: ' : '詞庫版本：'}${lexiconVersion}${showOpfsBackend ? ' · OPFS' : ''}`
      : null;

  return (
    <div className="app-actions mode-menu-root" ref={rootRef}>
      <div className="mode-menu-stack">
        <div className="mode-menu-anchor">
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
            <div className="menu-group" role="group" aria-label={lang === 'zh' ? '搜尋模式' : 'Search modes'}>
              <p className="menu-label">{lang === 'zh' ? '搜尋模式' : 'Search modes'}</p>
              {MODE_OPTIONS.map((option) => {
                const optionMeta = getModeMeta(
                  option.uiMode === '0243' ? 'm1' : option.uiMode === 'pingze' ? 'pz' : 'syn',
                  lang,
                );
                const checked = option.family === family;
                return (
                  <button
                    key={option.uiMode}
                    type="button"
                    className="mode-option"
                    role="menuitemradio"
                    aria-checked={checked}
                    disabled={disabled}
                    onClick={() => pickMode(option.family)}
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
            {onOpenWorkbench ? (
              <div className="menu-group workbench-menu-group" role="group" aria-label={lang === 'zh' ? '功能頁' : 'Feature pages'}>
                <p className="menu-label">{lang === 'zh' ? '功能頁' : 'Feature pages'}</p>
                <button
                  type="button"
                  className="mode-option"
                  role="menuitem"
                  onClick={() => {
                    close();
                    onOpenWorkbench();
                  }}
                >
                  <span>
                    <span className="mode-name">{lang === 'zh' ? '句格工作台' : 'Line Workbench'}</span>
                    <span className="mode-help">{lang === 'zh' ? '逐格掌握聲調、押韻與原意' : 'Shape tone, rhyme and meaning slot by slot'}</span>
                  </span>
                  <span className="mode-key">↗</span>
                </button>
              </div>
            ) : null}
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
              {onOpenRelation ? (
                <button
                  type="button"
                  className="mode-option"
                  role="menuitem"
                  onClick={() => {
                    onOpenRelation();
                    close();
                  }}
                >
                  <span>
                    <span className="mode-name">{lang === 'zh' ? '補關係' : 'Add relations'}</span>
                    <span className="mode-help">
                      {lang === 'zh' ? '為已收錄字面補近義或反義' : 'Add synonym or antonym links'}
                    </span>
                  </span>
                  <span className="mode-key">+</span>
                </button>
              ) : null}
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
              {onExitPortable ? (
                <button
                  type="button"
                  className="mode-option"
                  id="portableExitBtn"
                  role="menuitem"
                  onClick={() => {
                    close();
                    onExitPortable();
                  }}
                >
                  <span>
                    <span className="mode-name">{lang === 'zh' ? '退出 Canto-0243' : 'Exit Canto-0243'}</span>
                    <span className="mode-help">
                      {lang === 'zh' ? '關閉本機查韻服務' : 'Stop the local server'}
                    </span>
                  </span>
                </button>
              ) : null}
            </div>

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
      </div>
      {metaLabel ? (
        <p className="mode-menu-meta" aria-label={metaLabel}>
          {metaLabel}
        </p>
      ) : null}
    </div>
  );
}
