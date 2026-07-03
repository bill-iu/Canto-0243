import { useEffect, useId, useRef, useState } from 'react';

import { MODE_META, modeMetaFor, uiModeToUrlMode, type UiMode } from './mode-meta';

const MODE_OPTIONS: Array<{ uiMode: UiMode; key: string }> = [
  { uiMode: '0243', key: '0243' },
  { uiMode: '02493', key: '02493' },
  { uiMode: 'synonym', key: '~ / !' },
];

export interface ModeMenuProps {
  mode: UiMode;
  disabled?: boolean;
  onModeChange: (mode: UiMode) => void;
  onOpenGuide: () => void;
  onOpenAbout: () => void;
}

export function ModeMenu({
  mode,
  disabled = false,
  onModeChange,
  onOpenGuide,
  onOpenAbout,
}: ModeMenuProps) {
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const meta = modeMetaFor(mode);
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
        <div className="menu-group" role="group" aria-label="0243搜尋模式">
          <p className="menu-label">0243搜尋模式</p>
          {MODE_OPTIONS.map((option) => {
            const optionMeta = MODE_META[uiModeToUrlMode(option.uiMode)];
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
                  <span className="mode-help">{modeHelp(option.uiMode)}</span>
                </span>
                <span className="mode-key">{option.key}</span>
              </button>
            );
          })}
        </div>
        <div className="menu-group" role="group" aria-label="工具">
          <p className="menu-label">工具</p>
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
              <span className="mode-name">搜尋教學</span>
              <span className="mode-help">完整語法與例子</span>
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
              <span className="mode-name">關於</span>
              <span className="mode-help">授權、致謝與回報</span>
            </span>
            <span className="mode-key">i</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function modeHelp(uiMode: UiMode): string {
  if (uiMode === '0243') return '常用 0243 編碼與混合查詢';
  if (uiMode === '02493') return '02493 碼（分清二聲）';
  return '近義、反義與語意相關';
}

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p6-mode-menu-self-check.ts` */
export function modeMenuSelfCheck(): void {
  if (MODE_OPTIONS.length !== 3) {
    throw new Error('modeMenuSelfCheck: mode options');
  }
  if (modeHelp('synonym') !== '近義、反義與語意相關') {
    throw new Error('modeMenuSelfCheck: syn help');
  }
}
