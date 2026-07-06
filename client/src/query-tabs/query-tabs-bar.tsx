import { useRef } from 'react';
import { tabLabel, type QueryTab } from '@shared/query-tabs';
import { usePillTabDrag } from './use-pill-tab-drag';

export interface QueryTabsBarProps {
  tabs: QueryTab[];
  activeId: number;
  lang?: 'zh' | 'en';
  onSelect: (id: number) => void;
  onClose: (id: number) => void;
  onAdd: () => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
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
  const barRef = useRef<HTMLDivElement>(null);
  const tabIds = tabs.map((t) => t.id);

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
    <div ref={barRef} className="query-tabs-bar" role="tablist" aria-label={lang === 'en' ? 'Query tabs' : '查詢分頁'}>
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
              title={lang === 'en' ? 'Drag to reorder (desktop mouse; long-press on mobile)' : '拖曳以重排（桌面滑鼠；手機長按）'}
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
                aria-label={lang === 'en' ? `Close “${label}”` : `關閉「${label}」`}
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
        aria-label={lang === 'en' ? 'New query tab' : '新增查詢分頁'}
        title="Alt+N"
        onClick={onAdd}
      >
        +
      </button>
    </div>
  );
}
