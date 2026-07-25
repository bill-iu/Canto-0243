import { useEffect, useRef } from 'react';
import { tabLabel, type QueryTab } from '@shared/query-tabs';
import { getQueryTabCopy } from '../../../shared/query-tabs-i18n.mjs';
import { usePillTabDrag } from './use-pill-tab-drag';

export interface QueryTabsBarProps {
  tabs: QueryTab[];
  activeId: number;
  lang?: 'zh' | 'zh-Hans' | 'en';
  onSelect: (id: number) => void;
  onClose: (id: number) => void;
  onAdd: () => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
  /** Portable chrome-tabs: full order after drag (preferred over onReorder). */
  onReorderByIds?: (orderedIds: number[]) => void;
}

export function QueryTabsBar({
  tabs,
  activeId,
  lang = 'zh',
  onSelect,
  onClose,
  onAdd,
  onReorder,
}: QueryTabsBarProps) {
  const canClose = tabs.length > 1;
  const copy = getQueryTabCopy(lang);
  const barRef = useRef<HTMLDivElement>(null);
  const tabIds = tabs.map((t) => t.id);

  useEffect(() => {
    const active = barRef.current?.querySelector<HTMLElement>(`[data-tab-id="${activeId}"]`);
    active?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [activeId, tabs.length]);

  const {
    draggingId,
    touchArmId,
    overIndex,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handlePointerCancel,
    handleClick,
  } = usePillTabDrag({ tabIds, barRef, onSelect, onReorder });

  return (
    <div ref={barRef} className="query-tabs-bar" role="tablist" aria-label={copy.queryTabs}>
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeId;
        const label = tabLabel(tab, lang);
        const isDragging = draggingId === tab.id;
        const isTouchArmed = touchArmId === tab.id;
        const isDropTarget = overIndex === index && draggingId != null && !isDragging;
        return (
          <div
            key={tab.id}
            data-tab-id={tab.id}
            className={[
              'query-tab-pill',
              isActive ? 'is-active' : '',
              isDragging ? 'is-dragging' : '',
              isTouchArmed ? 'is-touch-armed' : '',
              isDropTarget ? 'is-drop-target' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            data-view={tab.view}
          >
            <button
              type="button"
              role="tab"
              className="query-tab-pill__label"
              aria-selected={isActive}
              tabIndex={isActive ? 0 : -1}
              title={copy.dragToReorder}
              onClick={(event) => {
                handleClick(event);
                if (!event.defaultPrevented) onSelect(tab.id);
              }}
              onPointerDown={(event) => handlePointerDown(event, tab.id)}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerCancel}
            >
              {label}
            </button>
            {canClose && (
              <button
                type="button"
                className="query-tab-pill__close"
                aria-label={copy.close(label)}
                onClick={(event) => {
                  event.stopPropagation();
                  onClose(tab.id);
                }}
              >
                ×
              </button>
            )}
          </div>
        );
      })}
      <button
        type="button"
        className="query-tab-add"
        aria-label={copy.newQuery}
        title="Alt+N"
        onClick={onAdd}
      >
        +
      </button>
    </div>
  );
}
