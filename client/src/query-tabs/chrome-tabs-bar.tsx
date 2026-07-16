/**
 * Portable-only chrome-tabs strip — wraps shared/chrome-tabs-layout.mjs.
 * PWA keeps QueryTabsBar pills; do not import this module from the PWA path.
 */
import { useEffect, useLayoutEffect, useRef } from 'react';
import { tabLabel, type QueryTab } from '@shared/query-tabs';
import { TAB_GEOMETRY_SVG } from '../../../shared/tab-geometry.mjs';
import { QueryChromeTabsLayout } from '../../../shared/chrome-tabs-layout.mjs';
import { ensureDraggabilly } from './ensure-draggabilly';
import type { QueryTabsBarProps } from './query-tabs-bar';

import '../../../shared/chrome-tabs.css';
import '../../../shared/query-tabs.css';

function applyActiveNeighborDividerHides(contentEl: Element) {
  contentEl.querySelectorAll('.chrome-tab').forEach((t) => {
    t.classList.remove('hide-left-divider-active', 'hide-right-divider-active');
  });
  const active = contentEl.querySelector('.chrome-tab[active]');
  if (!active) return;
  const prev = active.previousElementSibling;
  const next = active.nextElementSibling;
  if (prev?.classList.contains('chrome-tab') && !prev.classList.contains('chrome-tab-add')) {
    prev.classList.add('hide-right-divider-active');
  }
  if (next?.classList.contains('chrome-tab') && !next.classList.contains('chrome-tab-add')) {
    next.classList.add('hide-left-divider-active');
  }
}

function ChromeTabRow({
  tab,
  index,
  total,
  activeId,
  lang,
  canClose,
  onSelect,
  onClose,
}: {
  tab: QueryTab;
  index: number;
  total: number;
  activeId: number;
  lang: 'zh' | 'en';
  canClose: boolean;
  onSelect: (id: number) => void;
  onClose: (id: number) => void;
}) {
  const isActive = tab.id === activeId;
  const isLast = index === total - 1;
  const label = tabLabel(tab, lang);
  return (
    <div
      className={`chrome-tab${isLast ? ' chrome-tab-is-last' : ''}`}
      data-tab-id={tab.id}
      // chrome-tabs CSS selects [active]
      {...(isActive ? ({ active: '' } as Record<string, string>) : {})}
      role="presentation"
    >
      <div className="chrome-tab-dividers" />
      <div
        className="chrome-tab-background"
        dangerouslySetInnerHTML={{ __html: TAB_GEOMETRY_SVG }}
      />
      <div className="chrome-tab-content">
        <div className="chrome-tab-favicon" hidden />
        <div className="chrome-tab-title">{label}</div>
        <div
          className="chrome-tab-drag-handle"
          role="tab"
          tabIndex={isActive ? 0 : -1}
          aria-selected={isActive}
          aria-label={label}
          data-tab={tab.id}
          onClick={() => onSelect(tab.id)}
          onAuxClick={(event) => {
            if (event.button !== 1 || !canClose) return;
            event.preventDefault();
            onClose(tab.id);
          }}
        />
        {canClose ? (
          <button
            type="button"
            className="chrome-tab-close"
            aria-label={lang === 'en' ? `Close “${label}”` : `關閉「${label}」`}
            data-close={tab.id}
            onClick={(event) => {
              event.stopPropagation();
              onClose(tab.id);
            }}
          />
        ) : null}
      </div>
    </div>
  );
}

export function ChromeTabsBar({
  tabs,
  activeId,
  lang = 'zh',
  onSelect,
  onClose,
  onAdd,
  onReorderByIds,
}: QueryTabsBarProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const layoutRef = useRef<InstanceType<typeof QueryChromeTabsLayout> | null>(null);
  const canClose = tabs.length > 1;

  useEffect(() => {
    void ensureDraggabilly();
  }, []);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    if (!layoutRef.current) {
      layoutRef.current = new QueryChromeTabsLayout(root);
    }
    const layout = layoutRef.current;
    layout.layout();
    applyActiveNeighborDividerHides(layout.contentEl);

    let cancelled = false;
    void ensureDraggabilly().then(() => {
      if (cancelled || !layoutRef.current) return;
      layoutRef.current.setupDraggabilly({
        onPointerDown(id: number) {
          onSelect(id);
        },
        onReorderEnd(orderedIds: number[]) {
          onReorderByIds?.(orderedIds);
        },
      });
    });

    return () => {
      cancelled = true;
    };
  }, [tabs, activeId, onSelect, onReorderByIds]);

  useEffect(() => {
    const content = rootRef.current?.querySelector('.chrome-tabs-content');
    if (!content) return;

    const clearHoverFlags = () => {
      content.querySelectorAll('.chrome-tab').forEach((t) => {
        t.classList.remove('is-hovered', 'hide-left-divider-hover', 'hide-right-divider-hover');
      });
      applyActiveNeighborDividerHides(content);
    };

    const normals = [...content.querySelectorAll('.chrome-tab:not(.chrome-tab-add)')];
    const onEnter = (event: Event) => {
      const tab = event.currentTarget as Element;
      clearHoverFlags();
      tab.classList.add('is-hovered');
      const prev = tab.previousElementSibling;
      const next = tab.nextElementSibling;
      if (prev?.classList.contains('chrome-tab') && !prev.classList.contains('chrome-tab-add')) {
        prev.classList.add('hide-right-divider-hover');
      }
      if (next?.classList.contains('chrome-tab') && !next.classList.contains('chrome-tab-add')) {
        next.classList.add('hide-left-divider-hover');
      }
    };
    normals.forEach((tab) => {
      tab.addEventListener('mouseenter', onEnter);
      tab.addEventListener('mouseleave', clearHoverFlags);
    });
    applyActiveNeighborDividerHides(content);
    return () => {
      normals.forEach((tab) => {
        tab.removeEventListener('mouseenter', onEnter);
        tab.removeEventListener('mouseleave', clearHoverFlags);
      });
    };
  }, [tabs, activeId]);

  return (
    <div className="app-header__tabdeck" aria-label={lang === 'en' ? 'Query tabs' : '查詢分頁'}>
      <div className="tabdeck-strip" aria-label={lang === 'en' ? 'Chrome tabs strip' : '查詢分頁列（Chrome Tabs）'}>
        <div className="chrome-tabs" ref={rootRef}>
          <svg
            className="chrome-tabs-defs"
            aria-hidden="true"
            width="0"
            height="0"
            style={{ position: 'absolute' }}
          >
            <defs>
              <symbol id="query-tab-geometry" viewBox="0 0 214 36">
                <path d="M17 0h197v36H0v-2c4.5 0 9-3.5 9-8V8c0-4.5 3.5-8 8-8z" />
              </symbol>
            </defs>
          </svg>
          <div
            className="chrome-tabs-content"
            role="tablist"
            aria-label={lang === 'en' ? 'Query tabs' : '查詢分頁列'}
          >
            {tabs.map((tab, index) => (
              <ChromeTabRow
                key={tab.id}
                tab={tab}
                index={index}
                total={tabs.length}
                activeId={activeId}
                lang={lang}
                canClose={canClose}
                onSelect={onSelect}
                onClose={onClose}
              />
            ))}
            <div className="chrome-tab chrome-tab-add" role="presentation" data-add-tab>
              <div
                className="chrome-tab-add-hit"
                role="button"
                tabIndex={0}
                aria-label={lang === 'en' ? 'New query tab' : '新查詢分頁'}
                title="Alt+N"
                onClick={(event) => {
                  event.preventDefault();
                  onAdd();
                }}
                onKeyDown={(event) => {
                  if (event.key !== 'Enter' && event.key !== ' ') return;
                  event.preventDefault();
                  onAdd();
                }}
              >
                +
              </div>
            </div>
          </div>
          <div className="chrome-tabs-bottom-bar" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
