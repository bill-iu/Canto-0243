import { useEffect, useId, useRef, useState } from 'react';

import { getModeMeta, modeHelp, modeMetaFor, type UiMode } from './mode-meta';
import { searchFamilyForUiMode } from '../../contracts/search-mode-manifest.mjs';
import { getModeMenuCopy } from '../../shared/mode-menu-i18n.mjs';
import { MODE_OPTIONS } from './mode-menu-logic.ts';
import { isStopOnLastTabEnabled, setStopOnLastTabEnabled } from './desktop-session.ts';
import { isPortableHost } from './host-mode.ts';
import {
  IconSearch, IconPingze, IconSynonym,
  IconWorkbench, IconGuide, IconRelation, IconAbout, IconPower,
  IconSun, IconMoon,
} from './mode-menu-icons.tsx';

const MODE_MENU_GAP_PX = 12;
const MODE_MENU_MIN_SCALE = 0.75;

function fitModeMenuScale(opts: {
  naturalHeight: number;
  availableHeight: number;
  maxScale: number;
}): number {
  if (opts.naturalHeight <= opts.availableHeight + 0.5) return opts.maxScale;
  const ratio = opts.availableHeight / opts.naturalHeight;
  return Math.min(Math.max(ratio, MODE_MENU_MIN_SCALE), opts.maxScale);
}

export interface ModeMenuProps {
  mode: UiMode;
  disabled?: boolean;
  onModeChange: (family: 'basic' | 'pingze' | 'synonym') => void;
  onOpenGuide: () => void;
  onOpenAbout: () => void;
  onOpenWorkbench?: () => void;
  /** Portable host only — 關係補錄 */
  onOpenRelation?: () => void;
  /** Portable host only — 停止本機服務（keep-alive 模式先顯示） */
  onExitPortable?: () => void;
  theme?: 'light' | 'dark';
  lang?: 'zh' | 'zh-Hans' | 'en';
  onThemeChange?: (theme: 'light' | 'dark') => void;
  onLangChange?: (lang: 'zh' | 'zh-Hans' | 'en') => void;
  entrySize?: 'small' | 'medium' | 'large';
  onEntrySizeChange?: (size: 'small' | 'medium' | 'large') => void;
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
  entrySize = 'medium',
  onEntrySizeChange,
  lexiconVersion,
  showOpfsBackend = false,
}: ModeMenuProps) {
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [stopOnLastTab, setStopOnLastTab] = useState(() => isStopOnLastTabEnabled());
  // keep-alive mode (last-tab stop OFF) → show explicit stop control
  const showExit = Boolean(onExitPortable) && !stopOnLastTab;

  useEffect(() => {
    if (!isPortableHost()) return;
    const sync = () => setStopOnLastTab(isStopOnLastTabEnabled());
    window.addEventListener('canto-desktop-stop-mode', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('canto-desktop-stop-mode', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);
  const meta = modeMetaFor(mode, lang);
  const family = searchFamilyForUiMode(mode);
  const copy = getModeMenuCopy(lang);

  // ponytail: fit mode-menu to viewport — scale down + scroll fallback when overflow
  useEffect(() => {
    if (!open) {
      const menu = menuRef.current;
      if (menu) menu.style.removeProperty('--mode-menu-scale');
      return;
    }
    const menu = menuRef.current;
    if (!menu) return;
    const apply = () => {
      const trigger = rootRef.current?.querySelector('.menu-trigger')?.getBoundingClientRect();
      if (!trigger) return;
      const vh = window.visualViewport?.height ?? window.innerHeight;
      const availableHeight = vh - trigger.bottom - MODE_MENU_GAP_PX;
      const isNarrow = window.innerWidth <= 760;
      const scale = fitModeMenuScale({
        naturalHeight: menu.scrollHeight,
        availableHeight,
        maxScale: isNarrow ? 0.75 : 1,
      });
      menu.style.setProperty('--mode-menu-scale', String(scale));
    };
    apply();
    window.addEventListener('resize', apply);
    window.visualViewport?.addEventListener('resize', apply);
    return () => {
      window.removeEventListener('resize', apply);
      window.visualViewport?.removeEventListener('resize', apply);
    };
  }, [open]);

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
      ? `${copy.lexiconPrefix}${lexiconVersion}${showOpfsBackend ? ' · OPFS' : ''}`
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
            ref={menuRef}
            id={menuId}
            className={`mode-menu${open ? ' is-open' : ''}`}
            role="menu"
            aria-hidden={!open}
          >
            <div className="menu-group" role="group" aria-label={copy.groups.searchModes}>
              <p className="menu-label">{copy.groups.searchModes}</p>
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
                    <span className="mode-icon" aria-hidden="true">
                      {option.family === 'basic' ? <IconSearch /> : option.family === 'pingze' ? <IconPingze /> : <IconSynonym />}
                    </span>
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
              <div className="menu-group workbench-menu-group" role="group" aria-label={copy.groups.featurePages}>
                <p className="menu-label">{copy.groups.featurePages}</p>
                <button
                  type="button"
                  className="mode-option"
                  role="menuitem"
                  onClick={() => {
                    close();
                    onOpenWorkbench();
                  }}
                >
                  <span className="mode-icon" aria-hidden="true"><IconWorkbench /></span>
                  <span>
                    <span className="mode-name">{copy.workbench.title}</span>
                    <span className="mode-help">{copy.workbench.help}</span>
                  </span>
                  <span className="mode-key">↗</span>
                </button>
              </div>
            ) : null}
            <div className="menu-group" role="group" aria-label={copy.groups.tools}>
              <p className="menu-label">{copy.groups.tools}</p>
              <button
                type="button"
                className="mode-option"
                role="menuitem"
                onClick={() => {
                  onOpenGuide();
                  close();
                }}
              >
                  <span className="mode-icon" aria-hidden="true"><IconGuide /></span>
                  <span>
                    <span className="mode-name">{copy.guide.title}</span>
                    <span className="mode-help">{copy.guide.help}</span>
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
                  <span className="mode-icon" aria-hidden="true"><IconRelation /></span>
                  <span>
                    <span className="mode-name">{copy.relation.title}</span>
                    <span className="mode-help">
                      {copy.relation.help}
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
                <span className="mode-icon" aria-hidden="true"><IconAbout /></span>
                  <span>
                    <span className="mode-name">{copy.about.title}</span>
                    <span className="mode-help">{copy.about.help}</span>
                  </span>
                  <span className="mode-key">i</span>
              </button>
              {showExit ? (
                <button
                  type="button"
                  className="mode-option mode-option--danger"
                  id="portableExitBtn"
                  role="menuitem"
                  onClick={() => {
                    close();
                    onExitPortable?.();
                  }}
                >
                  <span className="mode-icon" aria-hidden="true"><IconPower /></span>
                  <span>
                    <span className="mode-name">
                      {copy.stopLocal.title}
                    </span>
                    <span className="mode-help">
                      {copy.stopLocal.help}
                    </span>
                  </span>
                </button>
              ) : null}
            </div>

            <div className="menu-group" role="group" aria-label={copy.groups.display}>
              <p className="menu-label">{copy.groups.display}</p>
              <div className="menu-switches">
                <button
                  type="button"
                  className="mode-option mode-switch"
                  onClick={() => {
                    onThemeChange?.(theme === 'dark' ? 'light' : 'dark');
                    close();
                  }}
                  aria-label={copy.displayControls.theme}
                >
                  <span aria-hidden="true">{theme === 'dark' ? <IconMoon /> : <IconSun />}</span>
                </button>
                <button
                  type="button"
                  className="mode-option mode-switch"
                  aria-pressed={lang === 'zh'}
                  onClick={() => {
                    if (lang !== 'zh') { onLangChange?.('zh'); close(); }
                  }}
                  aria-label={copy.displayControls.traditional}
                >
                  <span>繁</span>
                </button>
                <button
                  type="button"
                  className="mode-option mode-switch"
                  aria-pressed={lang === 'zh-Hans'}
                  onClick={() => {
                    if (lang !== 'zh-Hans') { onLangChange?.('zh-Hans'); close(); }
                  }}
                  aria-label={copy.displayControls.simplified}
                >
                  <span>简</span>
                </button>
                <button
                  type="button"
                  className="mode-option mode-switch"
                  aria-pressed={lang === 'en'}
                  onClick={() => {
                    if (lang !== 'en') { onLangChange?.('en'); close(); }
                  }}
                  aria-label={copy.displayControls.english}
                >
                  <span>EN</span>
                </button>
              </div>
              {isPortableHost() ? (
                <button
                  type="button"
                  className="mode-option"
                  role="menuitemcheckbox"
                  aria-checked={stopOnLastTab}
                  onClick={() => {
                    const next = !stopOnLastTab;
                    setStopOnLastTabEnabled(next);
                    setStopOnLastTab(next);
                  }}
                >
                  <span className="mode-icon" aria-hidden="true"><IconPower /></span>
                  <span>
                    <span className="mode-name">
                      {copy.stopMode.title}
                    </span>
                    <span className="mode-help">
                      {stopOnLastTab ? copy.stopMode.on : copy.stopMode.off}
                    </span>
                  </span>
                  <span className="mode-key" aria-hidden="true">
                    {stopOnLastTab ? '✓' : '○'}
                  </span>
                </button>
              ) : null}
            </div>

            <div className="menu-group" role="group" aria-label={copy.groups.textSize}>
              <p className="menu-label"><span className="menu-label-icon" aria-hidden="true">Aa</span> {copy.groups.textSize}</p>
              <div className="menu-switches menu-switches--entry-size">
                <button
                  type="button"
                  className="mode-option mode-switch"
                  aria-pressed={entrySize === 'small'}
                  onClick={() => {
                    onEntrySizeChange?.('small');
                    close();
                  }}
                >
                  {copy.entrySize.small}
                </button>
                <button
                  type="button"
                  className="mode-option mode-switch"
                  aria-pressed={entrySize === 'medium'}
                  onClick={() => {
                    onEntrySizeChange?.('medium');
                    close();
                  }}
                >
                  {copy.entrySize.medium}
                </button>
                <button
                  type="button"
                  className="mode-option mode-switch"
                  aria-pressed={entrySize === 'large'}
                  onClick={() => {
                    onEntrySizeChange?.('large');
                    close();
                  }}
                >
                  {copy.entrySize.large}
                </button>
              </div>
            </div>

            <div className="menu-group menu-group--github" role="group" aria-label="GitHub">
              <a
                className="mode-option mode-option--github"
                role="menuitem"
                href="https://github.com/bill-iu/Canto-0243"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => close()}
              >
                <span className="mode-option__github-lead">
                  <svg className="mode-option__github-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      fill="currentColor"
                      d="M12 2C6.477 2 2 6.486 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.342-3.369-1.342-.454-1.157-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.112-4.555-4.945 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.026 2.747-1.026.546 1.378.203 2.397.1 2.65.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.688-4.566 4.938.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.486 17.523 2 12 2z"
                    />
                  </svg>
                  <span>
                    <span className="mode-name">GitHub</span>
                    <span className="mode-help">
                      {copy.githubHelp}
                    </span>
                  </span>
                </span>
                <span className="mode-key" aria-hidden="true">↗</span>
              </a>
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
